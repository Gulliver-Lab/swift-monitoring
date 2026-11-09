use std::process::Command;

struct Node {
    name: String,
    mem_tot: u32,
    mem_used: u32,
    cpu_tot: u32,
    cpu_used: u32,
    gpu: Option<String>,
    gpu_used: bool,
}

fn print_node(node: Node) {
    println!("{}: ", node.name);
    println!("\t{}", node.mem_tot);
    println!("\t{}", node.mem_used);
    println!("\t{}", node.cpu_tot);
    println!("\t{}", node.cpu_used);
    match node.gpu {
        Some(i) => println!("\t{}", i),
        _ => println!("\tNone"),
    };

    println!("\t{}", node.gpu_used);
}

fn extract_gpu_name(s: &str) -> Option<String> {
    let start = s.find('_')? + 1;
    let rest = &s[start..];
    let end = rest.find(['-', ':', '_']).unwrap_or(rest.len());
    Some((&s[start..start + end]).to_string())
}

fn node_from_sinfo_line(line: &str) -> Option<Node> {
    let cpu_info = (&line[60..80]).trim().to_string();
    let split_cpu_info = cpu_info.split("/").collect::<Vec<&str>>();
    if split_cpu_info[2].parse::<u32>().unwrap() > 0 {
        return None;
    }

    return Some(Node {
        name: (&line[120..140]).trim().to_string(),
        mem_tot: (&line[20..40]).trim().parse().expect("Not valid number"),
        mem_used: (&line[40..60]).trim().parse().expect("Not valid number"),
        cpu_tot: split_cpu_info[3].parse().expect("Not valid number"),
        cpu_used: split_cpu_info[0].trim().parse().expect("Not valid number"),
        gpu: extract_gpu_name(&line[80..100]),
        gpu_used: (&line[100..120]).trim().to_string() != "(null)",
    });
}

fn read_sinfo() {
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

    let mut nodes: Vec<Node> = Vec::new();

    for line in output.lines() {
        let node = node_from_sinfo_line(line);
        match node {
            Some(i) => nodes.push(i),
            _ => (),
        }
    }

    for node in nodes {
        print_node(node);
    }
}

fn main() {
    read_sinfo();
}
