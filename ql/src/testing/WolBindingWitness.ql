/** @name WOL test-control binding witnesses
 * @description Raw access and declaration identities for frozen binding controls.
 * @kind table
 * @id ucode/testing/wol-binding-witness
 * @tags testing
 */
import codeql.ucode.AST
import codeql.ucode.ast.internal.AstNodes
import codeql.ucode.ast.internal.TreeSitter
from VariableAccess access, UCODE::AstNode occurrence, UCODE::AstNode declaration, string kind
where
  occurrence = toTreeSitter(access.getAstNode()) and
  declaration = toTreeSitter(access.getVariable().getAstNode()) and
  occurrence.getLocation().getFile().getBaseName() = [
    "nested_capture_write.uc", "nested_formal_disjoint.uc", "nested_formal_shadow.uc",
    "path_binding_shadow.uc"
  ] and
  (access instanceof VariableReadAccess and kind = "read" or
   access instanceof VariableWriteAccess and kind = "write")
select occurrence.getLocation().getFile().getRelativePath() as path, kind, occurrence,
  occurrence.getLocation().getStartLine(), occurrence.getLocation().getStartColumn(),
  occurrence.getLocation().getEndLine(), occurrence.getLocation().getEndColumn(),
  access.getVariable(), declaration, declaration.getAPrimaryQlClass(),
  declaration.getLocation().getStartLine(), declaration.getLocation().getStartColumn(),
  declaration.getLocation().getEndLine(), declaration.getLocation().getEndColumn()
