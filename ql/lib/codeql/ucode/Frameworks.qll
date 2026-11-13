/**
 * Framework and standard-library models for ucode.
 *
 * Identifier-keyed summarized callables (`system`, `popen`, `shellquote`)
 * exist so FlowSummary `getACall` can attach to identifier callees.
 * `propagatesFlow` stays `none()`. Member callees have no identifier.
 * Not production taint and not `path_found`.
 */

private import codeql.ucode.dataflow.FlowSummary

/**
 * A string-keyed summary named after an identifier callee.
 *
 * `getACall` matches `Call.getIdentifier` to this string. No flow:
 * `propagatesFlow` stays `none()`. Does not wire summary steps into
 * `localFlowStep`.
 */
private class IdentifierCalleeSummary extends SummarizedCallable::Range {
  IdentifierCalleeSummary() { this = ["system", "popen", "shellquote"] }

  override predicate propagatesFlow(
    string input, string output, boolean preservesValue
  ) {
    none()
  }
}
