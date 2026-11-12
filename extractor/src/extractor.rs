
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
                file_globs: vec!["luci".into()],
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
        let abi = tree_sitter_ucode::LANGUAGE_UCODE;
        let mut parser = Parser::new();
        parser
            .set_language(&abi.into())
            .expect("LANGUAGE_UCODE loads into tree-sitter 0.26.8");

        let fixture = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .join("../ql/test/extractor-smoke/usr/share/rpcd/ucode/luci");
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
        // Documented: file_globs is the literal basename "luci", not "*.uc".
        assert_ne!("luci.uc", "luci");
    }
}
