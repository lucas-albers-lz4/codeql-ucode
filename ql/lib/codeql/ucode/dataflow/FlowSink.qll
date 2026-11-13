/**
 * Provides classes and predicates for defining flow sinks.
 *
 * `Range` is a local data-flow node class. It does **not** extend
 * `FlowSummaryImpl::Public::SinkElement`: that class is not in
 * `codeql/dataflow` 1.1.6. Models-as-data sink rows are declared in
 * `ModelsAsData` but are not interpreted into nodes. Not production taint
 * and not `path_found`.
 */

private import codeql.ucode.DataFlow

// Import all instances below. Frameworks is intentionally empty.
private module Sinks {
  private import codeql.ucode.Frameworks
  private import codeql.ucode.dataflow.internal.ModelsAsData
}

/** Provides the `Range` class used to define the extent of `FlowSink`. */
module FlowSink {
  /** A flow sink. */
  abstract class Range extends DataFlow::Node {
    bindingset[this]
    Range() { any() }

    /**
     * Holds if this element is a flow sink of kind `kind`, where data
     * flows in as described by `input`.
     */
    predicate isSink(string input, string kind) { none() }
  }
}

final class FlowSink = FlowSink::Range;
