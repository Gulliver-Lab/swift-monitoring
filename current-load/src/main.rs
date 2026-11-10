use anstyle::{AnsiColor, Style};
use std::process::Command;
use terminal_colorsaurus::{QueryOptions, ThemeMode, theme_mode};

struct Node {
    name: String,
    mem_total: u32,
    mem_used: u32,
    cpu_total: u32,
    cpu_used: u32,
    gpu: Option<String>,
    gpu_used: bool,
}

fn print_node(node: Node) {
    println!("{}: ", node.name);
    println!("\t{}", node.mem_total);
    println!("\t{}", node.mem_used);
    println!("\t{}", node.cpu_total);
    println!("\t{}", node.cpu_used);
    match node.gpu {
        Some(i) => println!("\t{}", i),
        _ => println!("\tNone"),
    };

    println!("\t{}", node.gpu_used);
}

fn display_node_progress(node: Node) {
    println!("{}", node.name);
    println!("{}", boxed_progress_bar(node.cpu_used, node.cpu_total, 30));
    println!("{}", boxed_progress_bar(node.mem_used, node.mem_total, 30));
    println!();
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

    Some(Node {
        name: line[120..140].trim().to_string(),
        mem_total: line[20..40].trim().parse().expect("Not valid number"),
        mem_used: line[40..60].trim().parse().expect("Not valid number"),
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

fn box_around(inner: &str, width: usize) -> String {
    let rule = "─".repeat(width);
    format!("┌{rule}┐\n│{inner}│\n└{rule}┘")
}

fn progress_bar(current: u32, max: u32, width: usize) -> String {
    let ratio = if max == 0 {
        0.0
    } else {
        (current as f32 / max as f32).clamp(0.0, 1.0)
    };

    let filled = (ratio * width as f32).round() as usize;

    let light = matches!(theme_mode(QueryOptions::default()), Ok(ThemeMode::Light));

    let color = if light {
        AnsiColor::Green
    } else {
        AnsiColor::BrightGreen
    };

    let style = Style::new().fg_color(Some(color.into()));

    format!(
        "{style}{}{style:#}{}",
        //"█".repeat(filled),
        "█".repeat(filled),
        "─".repeat(width - filled),
    )
}

fn boxed_progress_bar(current: u32, max: u32, width: usize) -> String {
    let bar = progress_bar(current, max, width);
    box_around(&bar, width)
}

fn main() {
    call_and_parse_sinfo();
}
