/**
 * Provides ucode-specific definitions for use in the taint tracking library.
 */

private import codeql.Locations
private import codeql.dataflow.TaintTracking
private import DataFlowImplSpecific

module UcodeTaintTracking implements InputSig<Location, UcodeDataFlow> {
  import TaintTrackingPrivate
}
