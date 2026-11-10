use std::process::Command;

struct Node {
    name: String,
    mem_total: u32,
    mem_used: u32,
    cpu_total: u32,
    cpu_used: u32,
    gpu: Option<String>,
    gpu_used: bool,
}

fn display_node_progress(node: Node) {
    let cpu_flag = format!("{}/{}", node.cpu_used, node.cpu_total);
    let mem_flag = format!("{}/{}", node.mem_used, node.mem_total);
    println!(
        "{:<7} {} {:>7} {} {:>7}",
        node.name,
        progress_bar(node.cpu_used, node.cpu_total, 10),
        cpu_flag,
        progress_bar(node.mem_used, node.mem_total, 10),
        mem_flag,
    );
}

fn extract_gpu_name(s: &str) -> Option<String> {
    let start = s.find('_')? + 1;
    let rest = &s[start..];
    let end = rest.find(['-', ':', '_']).unwrap_or(rest.len());
    Some(s[start..start + end].to_string())
}

fn node_from_sinfo_line(line: &str) -> Option<Node> {
    let cpu_info = line[60..80].trim().to_string();
    let split_cpu_info = cpu_info.split("/").collect::<Vec<&str>>();
    if split_cpu_info[2].parse::<u32>().unwrap() > 0 {
        return None;
    }

    // Memory is in MB, we want to display GB
    Some(Node {
        name: line[120..140].trim().to_string(),
        mem_total: line[20..40]
            .trim()
            .parse::<u32>()
            .expect("Not valid number")
            / 1024,
        mem_used: line[40..60]
            .trim()
            .parse::<u32>()
            .expect("Not valid number")
            / 1024,
        cpu_total: split_cpu_info[3].parse().expect("Not valid number"),
        cpu_used: split_cpu_info[0].trim().parse().expect("Not valid number"),
        gpu: extract_gpu_name(&line[80..100]),
        gpu_used: line[100..120].trim() != "(null)",
    })
}

fn call_and_parse_sinfo() {
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

    let nodes: Vec<Node> = output.lines().filter_map(node_from_sinfo_line).collect();

    for node in nodes {
        // print_node(node);
        display_node_progress(node);
    }
}

const EIGHTHS: [char; 7] = ['▏', '▎', '▍', '▌', '▋', '▊', '▉'];

fn progress_bar(current: u32, max: u32, width: usize) -> String {
    let units = if max == 0 {
        0.0
    } else {
        (current as f32 / max as f32).clamp(0.0, 1.0) * width as f32 * 8.0
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

fn main() {
    call_and_parse_sinfo();
}
