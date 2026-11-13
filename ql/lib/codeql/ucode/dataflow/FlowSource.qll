/**
 * Provides classes and predicates for defining flow sources.
 *
 * `Range` is a local data-flow node class. It does **not** extend
 * `FlowSummaryImpl::Public::SourceElement`: that class is not in
 * `codeql/dataflow` 1.1.6. Models-as-data source rows are declared in
 * `ModelsAsData` but are not interpreted into nodes. Not production taint
 * and not `path_found`.
 */

private import codeql.ucode.DataFlow

// Import all instances below. Frameworks is intentionally empty.
private module Sources {
  private import codeql.ucode.Frameworks
  private import codeql.ucode.dataflow.internal.ModelsAsData
}

/** Provides the `Range` class used to define the extent of `FlowSource`. */
module FlowSource {
  /** A flow source. */
  abstract class Range extends DataFlow::Node {
    bindingset[this]
    Range() { any() }

    /**
     * Holds if this element is a flow source of kind `kind`, where data
     * flows out as described by `output`.
     */
    predicate isSource(string output, string kind) { none() }
  }
}

final class FlowSource = FlowSource::Range;
