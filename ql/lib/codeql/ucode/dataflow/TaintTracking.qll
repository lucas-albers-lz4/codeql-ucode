/**
 * Provides the module `TaintTracking`.
 */

private import ucode

/**
 * Provides a library for performing local (intra-procedural) and global
 * (inter-procedural) taint-tracking analyses.
 */
module TaintTracking {
  import codeql.ucode.dataflow.internal.TaintTrackingImpl::Public
  private import codeql.ucode.dataflow.internal.DataFlowImplSpecific
  private import codeql.ucode.dataflow.internal.TaintTrackingImplSpecific
  private import codeql.dataflow.TaintTracking
  private import ucode
  import TaintFlowMake<Location, UcodeDataFlow, UcodeTaintTracking>
}