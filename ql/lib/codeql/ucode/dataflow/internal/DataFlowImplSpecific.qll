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
 
 module ucodeDataFlow implements InputSig<Location> {
   import Private
   import Public
 
   class ParameterNode = Private::ParameterNodeImpl;
 
   Node exprNode(DataFlowExpr e) { result = Public::exprNode(e) }
 }