use std::process::Command;

struct Node {
    name: String,
    mem_tot: u32,
    mem_used: u32,
    cpu_tot: u32,
    cpu_used: u32,
    gpu: String,
    gpu_used: bool,
}

fn node_from_sinfo_line(line: String) -> Node {
    return Node {
        name: "node1".to_string(),
        mem_tot: (&line[20..40]).trim().parse().expect("Not valid number"),
        mem_used: (&line[40..60]).trim().parse().expect("Not valid number"),
        cpu_tot: (&line[20..40]).trim().parse().expect("Not valid number"),
        cpu_used: (&line[20..40]).trim().parse().expect("Not valid number"),
        gpu: "gpu".to_string(),
        gpu_used: false,
    };
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
        let node = node_from_sinfo_line(line.to_string());
        nodes.push(node);
    }
    println!("Read {} lines", nodes.len());
}

fn main() {
    read_sinfo();
}
