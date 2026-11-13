/**
 * Framework and standard-library models for ucode.
 *
 * Intentionally uninhabited: no stdlib summaries, sources, or sinks.
 * FlowSummary / FlowSource / FlowSink import this module as the instance
 * collection point. Not production taint and not `path_found`.
 */

/** Uninhabited sentinel so this module is a valid QL file. */
abstract class FrameworkModel extends string {
  FrameworkModel() { none() }
}
