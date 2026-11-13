/**
 * @name Field and Element content from extracted AST
 * @description Reports Field and Element Content values that match
 *              member properties or subscripts. Testing only. Not
 *              production taint, and not setInitAction path_found.
 * @kind problem
 * @problem.severity recommendation
 * @id ucode/extractor-smoke/content-encoding
 * @tags testing
 */

import codeql.files.FileSystem
import codeql.ucode.DataFlow
private import codeql.ucode.ast.internal.TreeSitter

private predicate extractedField(File f, string name) {
  exists(UCODE::MemberExpression m |
    name = m.getProperty().getValue() and
    f = m.getLocation().getFile()
  )
}

private predicate extractedElement(File f) {
  exists(UCODE::SubscriptExpression s | f = s.getLocation().getFile())
}

from File f, DataFlow::Content c, string label
where
  (f.getBaseName() = "luci" or f.getBaseName() = "ssa_neg") and
  (
    exists(string name |
      extractedField(f, name) and
      c.(DataFlow::FieldContent).getName() = name and
      label = "Field[" + name + "]"
    )
    or
    extractedElement(f) and
    c instanceof DataFlow::ElementContent and
    label = "Element"
  )
select f, label + " in " + f.getBaseName()
