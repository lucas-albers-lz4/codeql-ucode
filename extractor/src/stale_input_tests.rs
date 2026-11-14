use super::*;

fn test_root(name: &str) -> PathBuf {
    let root = std::env::temp_dir().join(format!("ucode-{name}-{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&root);
    std::fs::create_dir_all(&root).unwrap();
    root
}

#[test]
fn unresolved_input_is_reported_and_later_input_is_extracted() {
    let root = test_root("stale-input");
    let missing = root.join("missing.uc");
    let valid = root.join("valid.uc");
    let output = root.join("trap");
    let archive = root.join("archive");
    let source = b"let value = 1;\n";
    std::fs::write(&valid, source).unwrap();
    let valid = valid.canonicalize().unwrap();
    let lines = format!("{}\n{}\n", missing.display(), valid.display());
    let schema =
        node_types::read_node_types_str("ucode", tree_sitter_ucode::UCODE_NODE_TYPES).unwrap();
    let diagnostics = codeql_extractor::diagnostics::DiagnosticLoggers::new("ucode");

    let report = process_inputs(
        &lines,
        &schema,
        &diagnostics,
        &output,
        &archive,
        trap::Compression::Gzip,
    )
    .unwrap();
    assert!(report.is_reconciled());
    assert_eq!(
        (
            report.input_count,
            report.plain_count,
            report.uncertain_count
        ),
        (2, 1, 1)
    );
    let routing = std::fs::read_to_string(output.join("routing.json")).unwrap();
    assert!(routing.contains("\"reason\":\"input_path_unresolvable\""));
    assert!(routing.contains("\"inconclusive_reason\":\"input_path_unresolvable\""));
    assert!(routing.contains(&json_escape(&missing.display().to_string())));
    assert!(file_paths::path_for(&output, &valid, "trap.gz").is_file());
    assert_eq!(
        std::fs::read(file_paths::path_for(&archive, &valid, "")).unwrap(),
        source
    );
    std::fs::remove_dir_all(root).unwrap();
}

#[test]
fn output_directory_errors_are_not_skipped() {
    let root = test_root("stale-output-error");
    let output = root.join("not-a-directory");
    std::fs::write(&output, b"file").unwrap();
    let output_error = std::fs::create_dir_all(&output).unwrap_err();
    let schema =
        node_types::read_node_types_str("ucode", tree_sitter_ucode::UCODE_NODE_TYPES).unwrap();
    let diagnostics = codeql_extractor::diagnostics::DiagnosticLoggers::new("ucode");

    let result = process_inputs(
        &root.join("missing.uc").display().to_string(),
        &schema,
        &diagnostics,
        &output,
        &root.join("archive"),
        trap::Compression::Gzip,
    );
    assert_eq!(result.err().unwrap().kind(), output_error.kind());
    std::fs::remove_dir_all(root).unwrap();
}
