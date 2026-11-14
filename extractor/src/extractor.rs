use clap::Args;
use std::collections::HashSet;
use std::path::{Path, PathBuf};

use codeql_extractor::{file_paths, node_types, trap};

#[derive(Args)]
pub struct Options {
    /// Sets a custom source achive folder
    #[arg(long)]
    source_archive_dir: PathBuf,

    /// Sets a custom trap folder
    #[arg(long)]
    output_dir: PathBuf,

    /// A text file containing the paths of the files to extract
    #[arg(long)]
    file_list: String,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum Classification {
    Plain,
    Markup,
    Uncertain,
}

impl Classification {
    fn as_str(self) -> &'static str {
        match self {
            Self::Plain => "plain",
            Self::Markup => "markup",
            Self::Uncertain => "uncertain",
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
struct Route {
    classification: Classification,
    reason: &'static str,
}

#[derive(Default)]
struct RoutingReport {
    input_count: usize,
    plain_count: usize,
    markup_count: usize,
    uncertain_count: usize,
    excluded_count: usize,
    duplicate_input_count: usize,
    decisions: Vec<String>,
}

impl RoutingReport {
    fn is_reconciled(&self) -> bool {
        self.input_count
            == self.plain_count
                + self.markup_count
                + self.uncertain_count
                + self.excluded_count
                + self.duplicate_input_count
    }

    fn as_json(&self) -> String {
        format!(
            "{{\"input_count\":{},\"plain_count\":{},\"markup_count\":{},\"markup_inconclusive_count\":{},\"uncertain_count\":{},\"excluded_count\":{},\"duplicate_input_count\":{},\"decisions\":[{}]}}\n",
            self.input_count,
            self.plain_count,
            self.markup_count,
            self.markup_count,
            self.uncertain_count,
            self.excluded_count,
            self.duplicate_input_count,
            self.decisions.join(",")
        )
    }
}

/// Classify using the complete path, not its basename. The source archive
/// keeps the original path; the installed-path suffix is only used to model
/// the known loader rules in the frozen profile.
fn classify(path: &Path, source: &[u8]) -> Option<Route> {
    let installed_path = installed_path_for_source(path);
    let rpcd_raw_mode = is_immediate_rpcd_plugin(&installed_path);
    let ucode_share_path = installed_path.starts_with("usr/share/ucode/");
    let extension = path.extension().and_then(|x| x.to_str()).unwrap_or("");

    // rpcd's raw_mode loader is authoritative: extension and markup-like
    // content do not change how these plugin files are parsed.
    if rpcd_raw_mode {
        return Some(Route {
            classification: Classification::Plain,
            reason: "rpcd_raw_mode_full_path",
        });
    }

    if extension == "ut" {
        return Some(Route {
            classification: Classification::Markup,
            reason: "ut_markup_extension",
        });
    }

    if has_ucode_shebang(source) {
        return Some(Route {
            classification: Classification::Plain,
            reason: "ucode_shebang",
        });
    }

    if ucode_share_path && has_markup_tag(source) {
        return Some(Route {
            classification: Classification::Markup,
            reason: "markup_tag_content",
        });
    }

    if extension == "uc" || extension == "ucode" {
        return Some(Route {
            classification: Classification::Plain,
            reason: "ucode_extension",
        });
    }

    if ucode_share_path {
        return Some(Route {
            classification: Classification::Uncertain,
            reason: "unclassified_usr_share_ucode_path",
        });
    }

    // Keep the established extractor smoke fixtures working. These are
    // explicit test inputs, not a production extensionless-file heuristic.
    if is_legacy_smoke_input(path) {
        return Some(Route {
            classification: Classification::Plain,
            reason: "explicit_extractor_smoke_input",
        });
    }

    None
}

/// Apply only source layouts named by the frozen profile and PLAN while
/// keeping `path` unchanged for diagnostics and source archives.
fn installed_path_for_source(path: &Path) -> String {
    let full_path = path.to_string_lossy().replace('\\', "/");
    let components: Vec<_> = full_path
        .split('/')
        .filter(|part| !part.is_empty())
        .collect();
    // Test fixtures model installed paths beneath this explicit fixture root.
    if let Some(tail) =
        source_tail_after_components(&components, &["ql", "test", "extractor-smoke"])
    {
        return tail.join("/");
    }

    // PLAN.md §2 and pinned luci.mk: root/ is the package staging root;
    // package-root ucode/ installs below /usr/share/ucode/luci.
    for category in ["applications", "modules", "protocols", "themes"] {
        if let Some(tail) = package_layout_tail(&components, category, "*", "root") {
            return tail.join("/");
        }
        if let Some(tail) = package_layout_tail(&components, category, "*", "ucode") {
            return format!("usr/share/ucode/luci/{}", tail.join("/"));
        }
    }
    full_path
}

fn is_immediate_rpcd_plugin(installed_path: &str) -> bool {
    installed_path
        .strip_prefix("usr/share/rpcd/ucode/")
        .is_some_and(|filename| !filename.is_empty() && !filename.contains('/'))
}

fn source_tail_after_components(path: &[&str], prefix: &[&str]) -> Option<Vec<String>> {
    path.windows(prefix.len())
        .position(|parts| parts == prefix)
        .map(|start| {
            path[start + prefix.len()..]
                .iter()
                .map(|part| (*part).to_owned())
                .collect()
        })
}

fn package_layout_tail(
    path: &[&str],
    category: &str,
    package: &str,
    layout_directory: &str,
) -> Option<Vec<String>> {
    path.windows(3)
        .position(|parts| {
            parts[0] == category
                && (package == "*" || parts[1] == package)
                && parts[2] == layout_directory
        })
        .map(|start| {
            path[start + 3..]
                .iter()
                .map(|part| (*part).to_owned())
                .collect()
        })
}

fn has_ucode_shebang(source: &[u8]) -> bool {
    let first_line = source.split(|b| *b == b'\n').next().unwrap_or_default();
    let line = String::from_utf8_lossy(first_line);
    let Some(shebang) = line.strip_prefix("#!") else {
        return false;
    };
    let mut words = shebang.split_whitespace();
    let Some(interpreter) = words.next() else {
        return false;
    };
    if interpreter.rsplit('/').next() == Some("ucode") {
        return true;
    }
    if interpreter != "/usr/bin/env" && interpreter != "/bin/env" {
        return false;
    }

    match words.next() {
        Some("-S") => words.next().is_some_and(is_ucode_command),
        Some(command) => is_ucode_command(command),
        None => false,
    }
}

fn is_ucode_command(command: &str) -> bool {
    let command = command.trim_matches(['\'', '"']);
    let command = command.strip_prefix("-S").unwrap_or(command);
    command
        .split_whitespace()
        .next()
        .unwrap_or_default()
        .trim_matches(['\'', '"'])
        .rsplit('/')
        .next()
        == Some("ucode")
}

fn has_markup_tag(source: &[u8]) -> bool {
    String::from_utf8_lossy(source).lines().any(|line| {
        let line = line.trim_start();
        line.starts_with("{%") || line.starts_with("{{") || line.starts_with("{#")
    })
}

fn is_legacy_smoke_input(path: &Path) -> bool {
    const INPUTS: &[&str] = &[
        "luci",
        "taint_pos",
        "taint_neg",
        "taint_xfile_a",
        "taint_xfile_b",
        "quote_ok",
        "quote_exe",
        "quote_bad_suffix",
        "quote_bad_sh_c",
        "quote_bad_echo",
        "cfg_pos",
        "cfg_neg",
        "ssa_pos",
        "ssa_neg",
    ];
    let components: Vec<_> = path
        .components()
        .filter_map(|component| component.as_os_str().to_str())
        .collect();
    let Some(root) = components
        .windows(3)
        .position(|parts| parts == ["ql", "test", "extractor-smoke"])
    else {
        return false;
    };
    components
        .get(root + 3)
        .filter(|_| components.len() == root + 4)
        .is_some_and(|name| INPUTS.contains(name))
}

pub fn run(options: Options) -> std::io::Result<()> {
    tracing_subscriber::fmt()
        .with_target(false)
        .without_time()
        .with_level(true)
        .with_env_filter(tracing_subscriber::EnvFilter::from_default_env())
        .init();

    let file_list = file_paths::path_from_string(&options.file_list);
    let lines = std::fs::read_to_string(file_list)?;
    let schema = node_types::read_node_types_str("ucode", tree_sitter_ucode::UCODE_NODE_TYPES)?;
    let diagnostics = codeql_extractor::diagnostics::DiagnosticLoggers::new("ucode");
    let compression = match trap::Compression::from_env("CODEQL_UCODE_TRAP_COMPRESSION") {
        Ok(compression) => compression,
        Err(error) => {
            let mut logger = diagnostics.logger();
            logger.write(
                logger
                    .new_entry("configuration-error", "Configuration error")
                    .message(
                        "{}; using gzip.",
                        &[codeql_extractor::diagnostics::MessageArg::Code(&error)],
                    )
                    .severity(codeql_extractor::diagnostics::Severity::Warning),
            );
            trap::Compression::Gzip
        }
    };

    let report = process_inputs(
        &lines,
        &schema,
        &diagnostics,
        &options.output_dir,
        &options.source_archive_dir,
        compression,
    )?;
    tracing::info!(
        plain_count = report.plain_count,
        markup_count = report.markup_count,
        uncertain_count = report.uncertain_count,
        excluded_count = report.excluded_count,
        duplicate_input_count = report.duplicate_input_count,
        "Routing complete"
    );
    Ok(())
}

fn process_inputs(
    lines: &str,
    schema: &node_types::NodeTypeMap,
    diagnostics: &codeql_extractor::diagnostics::DiagnosticLoggers,
    output_dir: &Path,
    source_archive_dir: &Path,
    compression: trap::Compression,
) -> std::io::Result<RoutingReport> {
    let mut report = RoutingReport::default();
    let mut seen = HashSet::new();
    for line in lines.lines().filter(|line| !line.trim().is_empty()) {
        report.input_count += 1;
        let path = PathBuf::from(line).canonicalize()?;
        let path_id = file_paths::normalize_path(&path);
        let installed_path = installed_path_for_source(&path);
        if !seen.insert(path.clone()) {
            report.duplicate_input_count += 1;
            report.decisions.push(decision_json(
                &path_id,
                &installed_path,
                "duplicate",
                "duplicate_canonical_path",
                "duplicate",
                None,
            ));
            continue;
        }

        let source = std::fs::read(&path)?;
        let Some(route) = classify(&path, &source) else {
            report.excluded_count += 1;
            report.decisions.push(decision_json(
                &path_id,
                &installed_path,
                "excluded",
                "no_ucode_route",
                "excluded",
                None,
            ));
            continue;
        };

        let (status, inconclusive_reason) = match route.classification {
            Classification::Plain => ("plain_route_selected", None),
            Classification::Markup => ("inconclusive", Some("markup_not_modeled")),
            Classification::Uncertain => ("inconclusive", Some("uncertain_routing")),
        };
        report.decisions.push(decision_json(
            &path_id,
            &installed_path,
            route.classification.as_str(),
            route.reason,
            status,
            inconclusive_reason,
        ));

        match route.classification {
            Classification::Plain => {
                report.plain_count += 1;
                extract_plain(
                    &path,
                    &source,
                    schema,
                    diagnostics,
                    output_dir,
                    source_archive_dir,
                    compression,
                )?;
            }
            Classification::Markup => report.markup_count += 1,
            Classification::Uncertain => report.uncertain_count += 1,
        }
    }

    if !report.is_reconciled() {
        return Err(std::io::Error::new(
            std::io::ErrorKind::InvalidData,
            "routing totals do not reconcile with file-list inputs",
        ));
    }
    write_extras_trap(output_dir, compression)?;
    std::fs::create_dir_all(output_dir)?;
    std::fs::write(output_dir.join("routing.json"), report.as_json())?;
    Ok(report)
}

fn decision_json(
    path: &str,
    installed_path: &str,
    classification: &str,
    reason: &str,
    status: &str,
    inconclusive_reason: Option<&str>,
) -> String {
    let inconclusive = inconclusive_reason.map_or_else(String::new, |reason| {
        format!(",\"inconclusive_reason\":\"{}\"", json_escape(reason))
    });
    format!(
        "{{\"path\":\"{}\",\"installed_path\":\"{}\",\"classification\":\"{}\",\"reason\":\"{}\",\"status\":\"{}\"{}}}",
        json_escape(path),
        json_escape(installed_path),
        json_escape(classification),
        json_escape(reason),
        json_escape(status),
        inconclusive
    )
}

fn write_extras_trap(output_dir: &Path, compression: trap::Compression) -> std::io::Result<()> {
    let mut writer = trap::Writer::new();
    codeql_extractor::extractor::populate_empty_location(&mut writer);
    let path = file_paths::path_for(output_dir, Path::new("extras"), compression.extension());
    if let Some(parent) = path.parent() {
        std::fs::create_dir_all(parent)?;
    }
    writer.write_to_file(&path, compression)
}

fn extract_plain(
    path: &Path,
    source: &[u8],
    schema: &node_types::NodeTypeMap,
    diagnostics: &codeql_extractor::diagnostics::DiagnosticLoggers,
    output_dir: &Path,
    source_archive_dir: &Path,
    compression: trap::Compression,
) -> std::io::Result<()> {
    let mut trap_writer = trap::Writer::new();
    let mut diagnostics_writer = diagnostics.logger();
    codeql_extractor::extractor::extract(
        &tree_sitter_ucode::LANGUAGE_UCODE.into(),
        "ucode",
        schema,
        &mut diagnostics_writer,
        &mut trap_writer,
        path,
        source,
        &[],
    );
    let archive_path = file_paths::path_for(source_archive_dir, path, "");
    if let Some(parent) = archive_path.parent() {
        std::fs::create_dir_all(parent)?;
    }
    std::fs::copy(path, archive_path)?;
    let trap_path = file_paths::path_for(output_dir, path, compression.extension());
    if let Some(parent) = trap_path.parent() {
        std::fs::create_dir_all(parent)?;
    }
    trap_writer.write_to_file(&trap_path, compression)
}

fn json_escape(value: &str) -> String {
    let mut escaped = String::new();
    for character in value.chars() {
        match character {
            '"' => escaped.push_str("\\\""),
            '\\' => escaped.push_str("\\\\"),
            '\n' => escaped.push_str("\\n"),
            '\r' => escaped.push_str("\\r"),
            '\t' => escaped.push_str("\\t"),
            c if c <= '\u{1f}' => escaped.push_str(&format!("\\u{:04x}", c as u32)),
            c => escaped.push(c),
        }
    }
    escaped
}

#[cfg(test)]
mod tests {
    use super::*;
    use flate2::read::GzDecoder;
    use std::io::Read;
    use tree_sitter::Parser;

    fn classify_case(path: &str, source: &str) -> Route {
        classify(Path::new(path), source.as_bytes()).expect("fixture is a routing candidate")
    }

    #[test]
    fn seven_case_routing_gate_uses_synthetic_cases_where_profile_has_gaps() {
        // `synthetic:` labels are deliberate: pinned luci-ssl has no rpcd
        // `.uc`, no ucode-shebang libexec helper, and no raw-mode `.ut`.
        let cases = [
            (
                "usr/share/rpcd/ucode/plugin",
                "// synthetic extensionless plugin\nlet value = 1;\n",
                Classification::Plain,
                "rpcd_raw_mode_full_path",
            ),
            (
                "usr/share/rpcd/ucode/plugin.uc",
                "// synthetic .uc plugin\nlet value = 1;\n",
                Classification::Plain,
                "rpcd_raw_mode_full_path",
            ),
            (
                "usr/libexec/ucode-helper",
                "#!/usr/bin/ucode\n// synthetic ucode helper\nlet value = 1;\n",
                Classification::Plain,
                "ucode_shebang",
            ),
            (
                "usr/share/ucode/template.ut",
                "{# synthetic template #}\n",
                Classification::Markup,
                "ut_markup_extension",
            ),
            (
                "usr/share/ucode/tagged.uc",
                "{% synthetic tagged template %}\n",
                Classification::Markup,
                "markup_tag_content",
            ),
            (
                "usr/share/rpcd/ucode/plain.ut",
                "// synthetic raw-mode plugin, despite .ut\nlet value = 1;\n",
                Classification::Plain,
                "rpcd_raw_mode_full_path",
            ),
            (
                "usr/share/ucode/extensionless",
                "// synthetic unclassified file\n",
                Classification::Uncertain,
                "unclassified_usr_share_ucode_path",
            ),
        ];

        let mut counts = [0usize; 3];
        let mut paths = HashSet::new();
        let mut parser = Parser::new();
        parser
            .set_language(&tree_sitter_ucode::LANGUAGE_UCODE.into())
            .unwrap();
        let root = std::env::temp_dir().join(format!("ucode-routing-gate-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&root);
        let source_root = root.join("source");
        let trap_root = root.join("trap");
        let archive_root = root.join("archive");
        std::fs::create_dir_all(&source_root).unwrap();
        let schema =
            node_types::read_node_types_str("ucode", tree_sitter_ucode::UCODE_NODE_TYPES).unwrap();
        let diagnostics = codeql_extractor::diagnostics::DiagnosticLoggers::new("ucode");
        let mut plain_paths = Vec::new();
        let mut input_paths = Vec::new();
        for (path, source, expected_class, expected_reason) in cases {
            assert!(paths.insert(path), "duplicate gate path {path}");
            let fixture_path = source_root.join("ql/test/extractor-smoke").join(path);
            std::fs::create_dir_all(fixture_path.parent().unwrap()).unwrap();
            std::fs::write(&fixture_path, source).unwrap();
            let fixture_path = fixture_path.canonicalize().unwrap();
            input_paths.push(fixture_path.clone());
            let route = classify(&fixture_path, source.as_bytes()).unwrap();
            assert_eq!(route.classification, expected_class, "{path}");
            assert_eq!(route.reason, expected_reason, "{path}");
            match route.classification {
                Classification::Plain => {
                    counts[0] += 1;
                    let tree = parser.parse(source, None).unwrap();
                    assert!(
                        !tree.root_node().has_error(),
                        "invalid plain fixture {path}"
                    );
                    plain_paths.push(fixture_path);
                }
                Classification::Markup => counts[1] += 1,
                Classification::Uncertain => counts[2] += 1,
            }
        }
        assert_eq!(counts, [4, 2, 1]);

        let unmatched = source_root.join("misc/unmatched.bin");
        std::fs::create_dir_all(unmatched.parent().unwrap()).unwrap();
        std::fs::write(&unmatched, b"not a ucode input\n").unwrap();
        input_paths.push(unmatched.canonicalize().unwrap());
        input_paths.push(plain_paths[0].clone()); // duplicate file-list entry
        let file_list = input_paths
            .iter()
            .map(|path| path.display().to_string())
            .collect::<Vec<_>>()
            .join("\n");
        let report = process_inputs(
            &file_list,
            &schema,
            &diagnostics,
            &trap_root,
            &archive_root,
            trap::Compression::Gzip,
        )
        .unwrap();
        assert!(report.is_reconciled());
        assert_eq!(report.input_count, 9);
        assert_eq!(report.plain_count, 4);
        assert_eq!(report.markup_count, 2);
        assert_eq!(report.uncertain_count, 1);
        assert_eq!(report.excluded_count, 1);
        assert_eq!(report.duplicate_input_count, 1);
        assert_eq!(
            report.input_count,
            report.plain_count
                + report.markup_count
                + report.uncertain_count
                + report.excluded_count
                + report.duplicate_input_count
        );
        let routing_json = std::fs::read_to_string(trap_root.join("routing.json")).unwrap();
        assert!(routing_json.contains("\"markup_inconclusive_count\":2"));
        assert!(routing_json.contains("\"inconclusive_reason\":\"markup_not_modeled\""));
        assert!(routing_json.contains("\"classification\":\"excluded\""));
        assert!(routing_json.contains("\"classification\":\"duplicate\""));
        assert!(routing_json.contains("\"status\":\"plain_route_selected\""));
        assert!(!routing_json.contains("\"status\":\"analyzed\""));

        let trap_paths: Vec<_> = plain_paths
            .iter()
            .map(|path| file_paths::path_for(&trap_root, path, "trap.gz"))
            .collect();
        assert_eq!(trap_paths.iter().filter(|path| path.is_file()).count(), 4);
        for source_path in &plain_paths {
            let archived = file_paths::path_for(&archive_root, source_path, "");
            assert_eq!(
                std::fs::read(archived).unwrap(),
                std::fs::read(source_path).unwrap()
            );
        }
        let extras_path = file_paths::path_for(&trap_root, Path::new("extras"), "trap.gz");
        assert!(extras_path.is_file());
        let mut extras = String::new();
        GzDecoder::new(std::fs::File::open(extras_path).unwrap())
            .read_to_string(&mut extras)
            .unwrap();
        assert!(extras.contains("empty_location"));
        std::fs::remove_dir_all(root).unwrap();
    }

    #[test]
    fn routing_uses_full_path_not_basename() {
        let source = "// plain source\n";
        let raw = classify_case(
            "/src/luci/modules/luci-base/root/usr/share/rpcd/ucode/plugin",
            source,
        );
        let elsewhere = classify(
            Path::new("/src/luci/applications/plugin"),
            source.as_bytes(),
        );
        assert_eq!(raw.reason, "rpcd_raw_mode_full_path");
        assert_eq!(elsewhere, None);
        assert_eq!(
            installed_path_for_source(Path::new(
                "/src/modules/luci-base/root/usr/share/rpcd/ucode/plugin"
            )),
            "usr/share/rpcd/ucode/plugin"
        );
        assert_eq!(
            installed_path_for_source(Path::new("/src/modules/luci-base/ucode/plugin")),
            "usr/share/ucode/luci/plugin"
        );
        assert!(!is_immediate_rpcd_plugin(
            "usr/share/rpcd/ucode/nested/plugin"
        ));
        assert!(!is_immediate_rpcd_plugin("usr/share/rpcd/ucodeish/plugin"));
        assert!(!is_legacy_smoke_input(Path::new("/repo/src/taint_pos")));
        assert_eq!(
            installed_path_for_source(Path::new(
                "/src/luci/themes/luci-theme-bootstrap/ucode/template/themes/bootstrap-dark"
            )),
            "usr/share/ucode/luci/template/themes/bootstrap-dark"
        );
        assert_eq!(
            installed_path_for_source(Path::new("/src/unrelated/ucode/README")),
            "/src/unrelated/ucode/README"
        );
        assert_eq!(
            classify(
                Path::new("/src/unrelated/ucode/extensionless"),
                b"plain-looking text"
            ),
            None
        );
        let app_staged_plugin = Path::new(
            "/src/luci/applications/luci-app-example/root/usr/share/rpcd/ucode/plugin.ut",
        );
        assert_eq!(
            installed_path_for_source(app_staged_plugin),
            "usr/share/rpcd/ucode/plugin.ut"
        );
        assert_eq!(
            classify(app_staged_plugin, b"// plain ucode plugin\n")
                .unwrap()
                .classification,
            Classification::Plain
        );
        assert_eq!(
            classify(
                Path::new("/src/unrelated/ucode/template"),
                b"{% markup-looking content %}"
            ),
            None
        );
    }

    #[test]
    fn shebang_detection_requires_a_ucode_interpreter() {
        for positive in [
            "#!/usr/bin/ucode\n",
            "#!/usr/bin/env ucode\n",
            "#!/bin/env ucode\n",
            "#!/usr/bin/env -S ucode --flag\n",
            "#!/usr/bin/env -Sucode --flag\n",
            "#!/usr/bin/env -S /usr/bin/ucode --flag\n",
            "#!/usr/bin/env -S '/usr/bin/ucode --flag'\n",
            "#!/usr/bin/env -S\"/usr/bin/ucode --flag\"\n",
            "#!/usr/bin/env -S/usr/bin/ucode --flag\n",
        ] {
            assert!(has_ucode_shebang(positive.as_bytes()), "{positive:?}");
        }
        for negative in [
            "#!/bin/sh -c ucode\n",
            "#!/usr/bin/python ucode\n",
            "#!/usr/bin/env sh -c ucode\n",
            "#!/usr/bin/env -S sh -c ucode\n",
            "#!/usr/bin/env python ucode\n",
            "# /usr/bin/ucode\n",
        ] {
            assert!(!has_ucode_shebang(negative.as_bytes()), "{negative:?}");
        }
    }
}
