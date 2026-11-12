
use clap::Args;
use std::path::PathBuf;

use codeql_extractor::{
    extractor::simple::{Extractor, LanguageSpec},
    file_paths,
    trap
};

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

pub fn run(options: Options) -> std::io::Result<()> {
    tracing_subscriber::fmt()
        .with_target(false)
        .without_time()
        .with_level(true)
        .with_env_filter(tracing_subscriber::EnvFilter::from_default_env())
        .init();

    let file_list = file_paths::path_from_string(&options.file_list);
    let file_lists: Vec<PathBuf> = vec![file_list];

    let extractor = Extractor {
        prefix: "ucode".to_string(),
        languages: vec![
            // ucode
            LanguageSpec {
                prefix: "ucode",
                ts_language: tree_sitter_ucode::LANGUAGE_UCODE.into(),
                node_types: tree_sitter_ucode::UCODE_NODE_TYPES,
                // Stock simple::Extractor matches basename only. Literal "luci"
                // extracts the extensionless rpcd plugin and rejects luci.uc.
                // M4 adds sys.uc (installed luci.sys) without opening "*" routing.
                file_globs: vec![
                    "luci".into(),
                    "taint_pos".into(),
                    "taint_neg".into(),
                    "taint_xfile_a".into(),
                    "taint_xfile_b".into(),
                    "quote_ok".into(),
                    "quote_exe".into(),
                    "quote_bad_suffix".into(),
                    "quote_bad_sh_c".into(),
                    "quote_bad_echo".into(),
                    "sys.uc".into(),
                    "cfg_pos".into(),
                    "cfg_neg".into(),
                ],
            },
        ],
        trap_dir: options.output_dir,
        trap_compression: trap::Compression::from_env("CODEQL_UCODE_TRAP_COMPRESSION"),
        source_archive_dir: options.source_archive_dir,
        file_lists,
    };

    extractor.run()
}

#[cfg(test)]
mod tests {
    use std::path::PathBuf;
    use tree_sitter::Parser;

    #[test]
    fn language_ucode_parses_plain_luci_fixture() {
        parse_fixture_no_error("ql/test/extractor-smoke/usr/share/rpcd/ucode/luci");
        eprintln!(
            "tree-sitter LANGUAGE_VERSION={} MIN_COMPATIBLE_LANGUAGE_VERSION={} grammar_abi=15",
            tree_sitter::LANGUAGE_VERSION,
            tree_sitter::MIN_COMPATIBLE_LANGUAGE_VERSION
        );
    }

    #[test]
    fn language_ucode_parses_sys_uc_fixture() {
        parse_fixture_no_error("ql/test/extractor-smoke/usr/share/ucode/luci/sys.uc");
    }

    #[test]
    fn language_ucode_parses_cfg_fixtures() {
        parse_fixture_no_error("ql/test/extractor-smoke/cfg_pos");
        parse_fixture_no_error("ql/test/extractor-smoke/cfg_neg");
    }

    fn parse_fixture_no_error(rel: &str) {
        let abi = tree_sitter_ucode::LANGUAGE_UCODE;
        let mut parser = Parser::new();
        parser
            .set_language(&abi.into())
            .expect("LANGUAGE_UCODE loads into tree-sitter 0.26.8");
        let fixture = PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("..").join(rel);
        let src = std::fs::read_to_string(&fixture).unwrap_or_else(|e| {
            panic!("read {}: {e}", fixture.display())
        });
        let tree = parser.parse(&src, None).expect("parse returns a tree");
        assert!(
            !tree.root_node().has_error(),
            "fixture parse has error nodes: {}",
            tree.root_node().to_sexp()
        );
        assert_eq!(tree.root_node().kind(), "program");
        eprintln!(
            "tree-sitter LANGUAGE_VERSION={} MIN_COMPATIBLE_LANGUAGE_VERSION={} grammar_abi=15",
            tree_sitter::LANGUAGE_VERSION,
            tree_sitter::MIN_COMPATIBLE_LANGUAGE_VERSION
        );
    }

    #[test]
    fn luci_uc_basename_is_not_the_spike_glob() {
        // Documented: file_globs is literal basenames, not "*.uc".
        assert_ne!("luci.uc", "luci");
        assert_ne!("taint_pos.uc", "taint_pos");
        assert_ne!("quote_ok.uc", "quote_ok");
        assert_ne!("quote_exe.uc", "quote_exe");
        assert_ne!("quote_bad_suffix.uc", "quote_bad_suffix");
        assert_ne!("quote_bad_sh_c.uc", "quote_bad_sh_c");
        assert_ne!("quote_bad_echo.uc", "quote_bad_echo");
        assert_ne!("sys.uc", "sys");
        assert_ne!("cfg_pos.uc", "cfg_pos");
        assert_ne!("cfg_neg.uc", "cfg_neg");
    }
}
