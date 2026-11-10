use std::collections::HashMap;
use std::process::Command;

// MODELS

#[derive(Clone, Copy)]
struct Gauge {
    current: u64,
    max: u64,
}

struct Node {
    name: String,
    memory: Gauge,
    cpu: Gauge,
    gpu: Option<String>,
    gpu_used: bool,
}

struct Partition {
    nodes: Vec<Node>,
}

trait Progress {
    fn current(&self) -> u64;
    fn max(&self) -> u64;
}

impl Progress for Gauge {
    fn current(&self) -> u64 {
        self.current
    }
    fn max(&self) -> u64 {
        self.max
    }
}

// PARSING

fn extract_gpu_name(s: &str) -> Option<String> {
    let start = s.find('_')? + 1;
    let rest = &s[start..];
    let end = rest.find(['-', ':', '_']).unwrap_or(rest.len());
    Some(s[start..start + end].to_string())
}

fn node_from_sinfo_line(line: &str) -> Option<Node> {
    let cpu_info = line[60..80].trim().to_string();
    let split_cpu_info = cpu_info.split("/").collect::<Vec<&str>>();
    if split_cpu_info[2].parse::<u64>().unwrap() > 0 {
        return None;
    }

    // Memory is in MB, we want to display GB
    Some(Node {
        name: line[120..140].trim().to_string(),
        memory: Gauge {
            current: line[20..40]
                .trim()
                .parse::<u64>()
                .expect("Not valid number")
                / 1024,
            max: line[40..60]
                .trim()
                .parse::<u64>()
                .expect("Not valid number")
                / 1024,
        },
        cpu: Gauge {
            current: split_cpu_info[3].parse().expect("Not valid number"),
            max: split_cpu_info[0].trim().parse().expect("Not valid number"),
        },
        gpu: extract_gpu_name(&line[80..100]),
        gpu_used: line[100..120].trim() != "(null)",
    })
}

fn call_and_parse_sinfo() -> HashMap<String, Partition> {
    let sinfo_process = Command::new("sinfo")
        .args([
            "-h",
            "-N",
            "-O",
            "Partition,Memory,AllocMem,CPUsState,Gres,GresUsed,NodeList",
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

// DISPLAY

const EIGHTHS: [char; 7] = ['▏', '▎', '▍', '▌', '▋', '▊', '▉'];

fn progress_bar<T: Progress>(progress: T, width: usize) -> String {
    let units = if progress.max() == 0 {
        0.0
    } else {
        (progress.current() as f64 / progress.max() as f64).clamp(0.0, 1.0) * width as f64 * 8.0
    };

    let full = (units / 8.0) as usize;
    let rem = (units % 8.0) as usize;
    if rem == 0 {
        format!("{}{}", "█".repeat(full), " ".repeat(width - full))
    } else {
        let tail = EIGHTHS
            .get(rem - 1)
            .copied()
            .map(|c| c.to_string())
            .unwrap_or_default();
        //println!("There: {} {} {}", units, full, rem);
        format!(
            "{}{}{}",
            "█".repeat(full),
            tail,
            " ".repeat(width - full - 1)
        )
    }
}

fn progress_bar_with_counter<T: Progress>(progress: T, width: usize) -> String {
    let counter = format!("{}/{}", progress.current(), progress.max());
    format!("{} {:>7}", progress_bar(progress, width), counter)
}

fn display_partition(name: &str, partition: &Partition) {
    println!("{name}");
    let bar_width = 10;
    for node in &partition.nodes {
        println!(
            "{:<7} {} {}",
            node.name,
            progress_bar_with_counter(node.cpu, bar_width),
            progress_bar_with_counter(node.memory, bar_width)
        );
    }
}

// MAIN

fn main() {
    let partition_dict = call_and_parse_sinfo();
    for (partition_name, partition) in &partition_dict {
        display_partition(partition_name, partition);
    }
}
