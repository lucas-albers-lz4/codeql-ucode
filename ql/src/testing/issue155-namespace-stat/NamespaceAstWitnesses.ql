/** @name Testing-only namespace fs AST witnesses
 * @description Exact raw node identities and spans for namespace model controls.
 * @kind table
 * @id ucode/testing/issue155-namespace-ast-witnesses
 * @tags testing
 */
import codeql.files.FileSystem
import codeql.ucode.ast.internal.TreeSitter

private string spelling(UCODE::AstNode node) {
  exists(UCODE::Identifier id | node = id and result = id.getValue())
  or exists(UCODE::PropertyIdentifier id | node = id and result = id.getValue())
  or not node instanceof UCODE::Identifier and
    not node instanceof UCODE::PropertyIdentifier and result = ""
}

from UCODE::AstNode node
where (node.getLocation().getFile().getBaseName().matches("%.uc") or
  node.getLocation().getFile().getBaseName() = "luci.advanced-reboot")
select node.getLocation().getFile().getBaseName() as path,
  node as entity, node.getAPrimaryQlClass() as kind, spelling(node) as name,
  node.getLocation().getStartLine() as start_line,
  node.getLocation().getStartColumn() as start_column,
  node.getLocation().getEndLine() as end_line,
  node.getLocation().getEndColumn() as end_column,
  node.getParent() as parent
