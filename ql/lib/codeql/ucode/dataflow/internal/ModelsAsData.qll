/**
 * Defines extensible predicates for contributing library models from data extensions.
 *
 * The extensible relations have the following columns:
 *
 * - Sources:
 *   `path; output; kind; provenance`
 * - Sinks:
 *   `path; input; kind; provenance`
 * - Summaries:
 *   `path; input; output; kind; provenance`
 *
 * Rows compile as data extensions. Summary rows can inhabit `SummarizedCallable`
 * by path string. Source/sink rows are **not** interpreted into nodes:
 * `SourceElement` / `SinkElement` are not in dataflow 1.1.6, and ucode has no
 * canonical-path / crate resolver. Not production taint and not `path_found`.
 */

private import codeql.ucode.dataflow.FlowSummary

/**
 * Holds if in a call to the function with path `path`, the value referred
 * to by `output` is a flow source of the given `kind`.
 *
 * Declared for MaD shape compatibility. Rows are not interpreted into
 * `FlowSource` nodes on this dataflow version.
 */
extensible predicate sourceModel(
  string path, string output, string kind, string provenance, QlBuiltins::ExtensionId madId
);

/**
 * Holds if in a call to the function with path `path`, the value referred
 * to by `input` is a flow sink of the given `kind`.
 *
 * Declared for MaD shape compatibility. Rows are not interpreted into
 * `FlowSink` nodes on this dataflow version.
 */
extensible predicate sinkModel(
  string path, string input, string kind, string provenance, QlBuiltins::ExtensionId madId
);

/**
 * Holds if in a call to the function with path `path`, the value referred
 * to by `input` can flow to the value referred to by `output`.
 *
 * `kind` should be either `value` or `taint`, for value-preserving or taint-preserving
 * steps, respectively. The summary compiles; it does not attach to source calls.
 */
extensible predicate summaryModel(
  string path, string input, string output, string kind, string provenance,
  QlBuiltins::ExtensionId madId
);

/**
 * Holds if the given extension tuple `madId` should pretty-print as `model`.
 *
 * This predicate should only be used in tests.
 */
predicate interpretModelForTest(QlBuiltins::ExtensionId madId, string model) {
  exists(string path, string output, string kind |
    sourceModel(path, output, kind, _, madId) and
    model = "Source: " + path + "; " + output + "; " + kind
  )
  or
  exists(string path, string input, string kind |
    sinkModel(path, input, kind, _, madId) and
    model = "Sink: " + path + "; " + input + "; " + kind
  )
  or
  exists(string path, string input, string output, string kind |
    summaryModel(path, input, output, kind, _, madId) and
    model = "Summary: " + path + "; " + input + "; " + output + "; " + kind
  )
}

/**
 * A summarized callable from a MaD summary row. Identified by the path string.
 * `FlowSummaryImpl` `getACall` is `none()`, so this does not apply to calls.
 */
private class SummarizedCallableFromModel extends SummarizedCallable::Range {
  private string path;

  SummarizedCallableFromModel() {
    summaryModel(path, _, _, _, _, _) and
    this = path
  }

  override predicate hasProvenance(Provenance provenance) {
    summaryModel(path, _, _, _, provenance, _)
  }

  override predicate propagatesFlow(
    string input, string output, boolean preservesValue, string model
  ) {
    exists(string kind, QlBuiltins::ExtensionId madId |
      summaryModel(path, input, output, kind, _, madId) and
      model = "MaD:" + madId.toString()
    |
      kind = "value" and
      preservesValue = true
      or
      kind = "taint" and
      preservesValue = false
    )
  }
}
