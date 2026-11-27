/** @name Issue 53 modeled variable accesses
 * @description All modeled reads and writes in the selected files, including raw identifier and declaration entities.
 * @kind table
 * @id ucode/testing/issue53-uci-variable-accesses
 */
import codeql.files.FileSystem
import codeql.ucode.AST
import codeql.ucode.ast.internal.AstNodes
import codeql.ucode.ast.internal.TreeSitter

from VariableAccess access, UCODE::AstNode rawAccess, UCODE::AstNode rawDeclaration, string kind
where
  (access.getLocation().getFile().getRelativePath() = "usr/share/rpcd/ucode/luci.adblock-fast" or
   access.getLocation().getFile().getRelativePath().matches("controls/%")) and
  rawAccess = toTreeSitter(access.getAstNode()) and
  rawDeclaration = toTreeSitter(access.getVariable().getAstNode()) and
  (access instanceof VariableReadAccess and kind = "read" or
   access instanceof VariableWriteAccess and kind = "write")
select access.getLocation().getFile().getRelativePath() as path, kind, access.getName() as name,
  rawAccess as raw_access, rawAccess.getPrimaryQlClasses() as raw_access_classes,
  rawAccess.getLocation().getStartLine() as start_line, rawAccess.getLocation().getStartColumn() as start_column,
  rawAccess.getLocation().getEndLine() as end_line, rawAccess.getLocation().getEndColumn() as end_column,
  access.getVariable() as variable, rawDeclaration as raw_declaration,
  rawDeclaration.getPrimaryQlClasses() as declaration_classes
