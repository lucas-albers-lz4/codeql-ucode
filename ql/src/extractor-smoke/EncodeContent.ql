/**
 * @name MaD encodeContent Field and Element tokens
 * @description Reports Field and Element MaD tokens from encodeContent.
 *              Testing only. Not production taint, and not
 *              setInitAction path_found.
 * @kind problem
 * @problem.severity recommendation
 * @id ucode/extractor-smoke/encode-content
 * @tags testing
 */

import codeql.files.FileSystem
import codeql.ucode.DataFlow
private import codeql.ucode.ast.internal.TreeSitter
private import codeql.ucode.dataflow.internal.FlowSummaryImpl

private predicate extractedField(File f, string name) {
  exists(UCODE::MemberExpression m |
    name = m.getProperty().getValue() and
    f = m.getLocation().getFile()
  )
}

private predicate extractedElement(File f) {
  exists(UCODE::SubscriptExpression s | f = s.getLocation().getFile())
}

from File f, DataFlow::ContentSet cs, string arg, string token, string label
where
  not exists(string futureArg | Input::encodeContent(_, futureArg) = "Future") and
  token = Input::encodeContent(cs, arg) and
  (f.getBaseName() = "luci" or f.getBaseName() = "ssa_neg") and
  (
    exists(DataFlow::FieldContent fc, string name |
      cs.isSingleton(fc) and
      fc.getName() = name and
      extractedField(f, name) and
      token = "Field" and
      arg = name and
      label = "Field[" + name + "]"
    )
    or
    exists(DataFlow::ElementContent ec |
      cs.isSingleton(ec) and
      extractedElement(f) and
      token = "Element" and
      arg = "" and
      label = "Element"
    )
  )
select f, label + " in " + f.getBaseName()
