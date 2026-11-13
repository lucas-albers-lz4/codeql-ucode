/**
 * @name Content store and read composition
 * @description Exercises literal containers and shorthand values through global flow.
 * @kind problem
 * @problem.severity recommendation
 * @id ucode/extractor-smoke/store-read-composition
 */

import codeql.ucode.DataFlow
private import codeql.ucode.ast.internal.AstNodes
private import codeql.ucode.ast.internal.TreeSitter

module Configuration implements DataFlow::ConfigSig {
  predicate isSource(DataFlow::Node n) {
    exists(UCODE::CallExpression call |
      toTreeSitter(n.asExpr().getExpr()) = call and
      call.getFunction().(UCODE::Identifier).getValue() = "source" and
      n.getLocation().getFile().getBaseName() = "ssa_neg"
    )
  }

  predicate isSink(DataFlow::Node n) {
    n.getLocation().getFile().getBaseName() = "ssa_neg" and
    (
      exists(UCODE::MemberExpression m |
        toTreeSitter(n.asExpr().getExpr()) = m and
        (
          m.getObject().(UCODE::Identifier).getValue() in [
              "literal_obj", "shorthand_obj", "shorthand_inner"
            ]
          or
          m.getProperty().getValue() = "inline_field"
        )
      )
      or
      exists(UCODE::SubscriptExpression s |
        toTreeSitter(n.asExpr().getExpr()) = s and
        s.getObject().(UCODE::Identifier).getValue() = "literal_arr"
      )
    )
  }
}

module Flow = DataFlow::Global<Configuration>;

from DataFlow::Node source, DataFlow::Node sink, string message
where
  Flow::flow(source, sink) and
  message =
    "flow:" + source.getLocation().getStartLine().toString() + ":" +
      sink.getLocation().getStartLine().toString()
  or
  exists(DataFlow::ContentContainerNode container, DataFlow::ReturnValueNode ret |
    source = container and
    sink = ret and
    container.getLocation().getFile().getBaseName() = "ssa_neg" and
    DataFlow::localFlow(container, ret) and
    message =
      "return:" + container.getLocation().getStartLine().toString() + ":" +
        ret.getLocation().getStartLine().toString()
  )
select sink, message
