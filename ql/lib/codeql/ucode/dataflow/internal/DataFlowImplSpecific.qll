/**
 * Provides ucode-specific definitions for use in the data flow library.
 */

private import ucode
private import codeql.dataflow.DataFlow

module Private {
  import DataFlowPrivate
  import DataFlowDispatch
}

module Public {
  import DataFlowPublic
}

module UcodeDataFlow implements InputSig<Location> {
  import Private
  import Public

  class ParameterNode = Private::ParameterNodeImpl;

  predicate isParameterNode(ParameterNode p, DataFlowCallable c, ParameterPosition pos) {
    Private::isParameterNode(p, c, pos)
  }

  Node exprNode(DataFlowExpr e) { result = Public::exprNode(e) }
}
