use std::collections::HashMap;
use std::env;
use std::process::Command;

// MODELS

#[derive(Clone, Copy)]
struct Gauge {
    mine: u64,
    all: u64,
    max: u64,
}

struct Node {
    name: String,
    memory: Gauge,
    cpu: Gauge,
    gpu: Option<String>,
    gpu_used: bool,
    gpu_used_by_me: bool,
}

struct Partition {
    nodes: Vec<Node>,
}

struct Colors {
    good: String,
    medium: String,
    bad: String,
    free: String,
    busy: String,
    mine: String,
}

trait Progress {
    fn all(&self) -> u64;
    fn max(&self) -> u64;
    fn ratio_all(&self) -> f64;
    fn ratio_mine(&self) -> f64;
}

impl Progress for Gauge {
    fn all(&self) -> u64 {
        self.all
    }
    fn max(&self) -> u64 {
        self.max
    }
    fn ratio_all(&self) -> f64 {
        (self.all as f64 / self.max as f64).clamp(0.0, 1.0)
    }
    fn ratio_mine(&self) -> f64 {
        (self.mine as f64 / self.max as f64).clamp(0.0, 1.0)
    }
}

// PARSING

fn extract_gpu_name(s: &str) -> Option<String> {
    let start = s.find('_')? + 1;
    let rest = &s[start..];
    let end = rest.find(['-', ':', '_']).unwrap_or(rest.len());
    Some(s[start..start + end].to_string())
}

fn is_gpu_used(s: &str) -> bool {
    if s.trim() == "(null)" {
        return false;
    };
    // stings have the format gpu:gpu_name:?(IDX: ?) where the first ? is the number of GPU used. We extract this
    let c = s.split(':').nth(2).unwrap().chars().next().unwrap();
    c == '1'
}

fn node_from_sinfo_line(line: &str) -> Option<Node> {
    let cpu_info = line[60..80].trim().to_string();
    let split_cpu_info = cpu_info.split("/").collect::<Vec<&str>>();
    if split_cpu_info[2].parse::<u64>().unwrap() > 0 {
        return None;
    }

    // Memory is in MB, we want to display GB
    Some(Node {
        name: line[140..160].trim().to_string(),
        memory: Gauge {
            mine: 0,
            all: line[40..60]
                .trim()
                .parse::<u64>()
                .expect("Not valid number")
                / 1024,
            max: line[20..40]
                .trim()
                .parse::<u64>()
                .expect("Not valid number")
                / 1024,
        },
        cpu: Gauge {
            mine: 0,
            all: split_cpu_info[0].parse().expect("Not valid number"),
            max: split_cpu_info[3].trim().parse().expect("Not valid number"),
        },
        gpu: extract_gpu_name(&line[80..100]),
        gpu_used: is_gpu_used(&line[100..140]),
        gpu_used_by_me: false,
    })
}

fn call_and_parse_sinfo() -> HashMap<String, Partition> {
    let sinfo_process = Command::new("sinfo")
        .args([
            "-h",
            "-N",
            "-O",
            "Partition,Memory,AllocMem,CPUsState,Gres,GresUsed:40,NodeList",
        ])
        .output()
        .expect("Failed to run sinfo");
    let output = String::from_utf8(sinfo_process.stdout).expect("Failed to decode sinfo output");

    let mut partition_dict = HashMap::<String, Partition>::new();
    for line in output.lines() {
        if let Some(node) = node_from_sinfo_line(line) {
            let partition_name = line[0..20].trim().to_string();
            if !partition_dict.contains_key(&partition_name) {
                partition_dict.insert(
                    partition_name.clone(),
                    Partition {
                        nodes: Vec::<Node>::new(),
                    },
                );
            }
            partition_dict
                .get_mut(&partition_name)
                .unwrap()
                .nodes
                .push(node);
        }
    }
    partition_dict
}

fn call_and_parse_squeue(username: Option<&str>) -> HashMap<String, (u64, u64, bool)> {
    let mut squeue_args = match username {
        Some(username) => vec!["-u".to_string(), username.to_string()],
        None => vec!["--me".to_string()],
    };
    squeue_args.extend(
        ["-h", "-t", "R", "-O", "MaxCPUs,NodeList,MinMemory"]
            .into_iter()
            .map(str::to_string),
    );

    let squeue_process = Command::new("squeue")
        .args(squeue_args)
        .output()
        .expect("Failed to run squeue");
    let output = String::from_utf8(squeue_process.stdout).expect("Failed to decode squeue output");

    let mut node_dict = HashMap::<String, (u64, u64, bool)>::new();
    for line in output.lines() {
        // format is ncpu, nodelist, ram, all with 20 char fixed width
        let n_cpu = line[0..20].trim().parse::<u64>().unwrap();
        let node_name = line[20..40].trim().to_string();
        // mem is something like 1G or 250M
        let mut mem_string = line[40..60].trim().to_string();
        let memory_mb = match mem_string.pop().unwrap() {
            'M' => mem_string.parse::<u64>().unwrap(),
            'G' => mem_string.parse::<u64>().unwrap() * 1024,
            _ => 0,
        };
        // The GRES column is either "N/A" or "gres/gpu:...", so only test first char
        let gpu_used_by_me = line[60..61] == "g".to_string();

        // cpu, mem
        let (sum_cpu, sum_memory, gpu_flag) = node_dict.entry(node_name).or_insert((0, 0, false));
        *sum_cpu += n_cpu;
        *sum_memory += memory_mb;
        *gpu_flag = *gpu_flag || gpu_used_by_me;
    }

    node_dict
}

// DISPLAY

const EIGHTHS: [char; 7] = ['▏', '▎', '▍', '▌', '▋', '▊', '▉'];

fn progress_bar<T: Progress>(progress: T, width: usize, colors: (&str, &str)) -> String {
    // With unicode, a character width can be divided into 8, but using appropriate characters (cf chars defined above)
    // units refer to the number of 1/8th that must be displayed

    // For everything running on the node
    let units_all = if progress.max() == 0 {
        0.0
    } else {
        progress.ratio_all() * width as f64 * 8.0
    };
    let mut full_all = (units_all / 8.0) as usize;
    let mut rem_all = (units_all % 8.0) as usize;

    // For my stuff only (other color)after a full
    let units_mine = if progress.max() == 0 {
        0.0
    } else {
        progress.ratio_mine() * width as f64 * 8.0
    };
    let mut full_mine = (units_mine / 8.0) as usize;
    let mut rem_mine = (units_mine % 8.0) as usize;

    // We can't change color inside a character, so the limit between all and mine must be between full units
    // We need to round to achieve that
    if (full_mine == full_all) && (rem_mine > 0) {
        if (rem_all <= 4) || (rem_mine >= 4) {
            rem_mine = rem_all;
            rem_all = 0;
        } else {
            rem_mine = 0;
        }
    } else {
        if rem_mine >= 4 {
            full_mine += 1;
        }
        rem_mine = 0;
    }
    full_all -= full_mine;

    let tail_all = if rem_all > 0 {
        EIGHTHS
            .get(rem_all - 1)
            .copied()
            .map(|c| c.to_string())
            .unwrap_or_default()
    } else {
        "".to_string()
    };
    let tail_mine = if rem_mine > 0 {
        EIGHTHS
            .get(rem_mine - 1)
            .copied()
            .map(|c| c.to_string())
            .unwrap_or_default()
    } else {
        "".to_string()
    };

    let (color_mine, color_all) = colors;
    format!(
        "{}{}{}{}{}{}{}\x1b[0m",
        color_mine,
        "█".repeat(full_mine),
        tail_mine,
        color_all,
        "█".repeat(full_all),
        tail_all,
        " ".repeat(
            width - full_all - full_mine - tail_all.chars().count() - tail_mine.chars().count()
        )
    )
}

fn progress_bar_with_counter<T: Progress>(
    progress: T,
    width: usize,
    colors: (&str, &str),
) -> String {
    let counter = format!("{}/{}", progress.all(), progress.max());
    format!("{} {:>7}", progress_bar(progress, width, colors), counter)
}

fn gpu_tag(node: &Node) -> String {
    if let Some(gpu_name) = &node.gpu {
        return format!("{:>4}", gpu_name);
    }
    "    ".to_string()
}

fn display_partition(name: &str, partition: &Partition, colors: &Colors) {
    let bar_width = 10;

    // name + (bar + counter) * 2 + GPU tag + spaces
    let inner_width = 7 + (bar_width + 9) * 2 + 4 + 9;

    println!(
        "┌─{}{}CPU{}RAM{}GPU─┐",
        name,
        "─".repeat(18 - name.len()),
        "─".repeat(18),
        "─".repeat(11),
    );

    for node in &partition.nodes {
        let node_cpu_color = if node.cpu.ratio_all() < 0.75 {
            &colors.good
        } else if node.cpu.ratio_all() < 0.95 {
            &colors.medium
        } else {
            &colors.bad
        };
        let node_ram_color = if node.memory.ratio_all() < 0.75 {
            &colors.good
        } else if node.cpu.ratio_all() < 0.95 {
            &colors.medium
        } else {
            &colors.bad
        };
        let gpu_color = if node.gpu_used_by_me {
            &colors.mine
        } else if node.gpu_used {
            &colors.busy
        } else {
            &colors.free
        };
        println!(
            "│ {:<7} │ {} │ {} │ {}\x1b[1m{}\x1b[0m │",
            node.name,
            progress_bar_with_counter(node.cpu, bar_width, (&colors.mine, node_cpu_color)),
            progress_bar_with_counter(node.memory, bar_width, (&colors.mine, node_ram_color)),
            gpu_color,
            gpu_tag(node)
        );
    }
    println!("└{}┘", "─".repeat(inner_width));
}

// MAIN

fn main() {
    let mut partition_dict = call_and_parse_sinfo();
    let node_dict = call_and_parse_squeue(env::args().nth(1).as_deref());
    for partition in partition_dict.values_mut() {
        for node in partition.nodes.iter_mut() {
            if node_dict.contains_key(&node.name) {
                let (my_cpu, my_memory_mb, my_gpu_flag) = node_dict.get(&node.name).unwrap();
                node.cpu.mine = *my_cpu;
                node.memory.mine = *my_memory_mb / 1024;
                node.gpu_used_by_me = *my_gpu_flag;
            }
        }
    }

    let colors = Colors {
        good: "\x1b[92m".to_string(),
        medium: "\x1b[93m".to_string(),
        bad: "\x1b[91m".to_string(),
        free: "\x1b[92m".to_string(),
        busy: "\x1b[91m".to_string(),
        mine: "\x1b[94m".to_string(),
    };

    let partition_order = ["ludocpu", "newcpu", "oldcpu"];
    for &partition_name in &partition_order {
        display_partition(
            partition_name,
            partition_dict.get(partition_name).unwrap(),
            &colors,
        );
    }
}
