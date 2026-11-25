/**
 * @name DDNS stat raw AST inventory (unfiltered)
 * @description Test-only raw AST identity and parent-edge inventory for frozen #155 inputs.
 *              No candidate, sink, or security classification is made.
 * @kind table
 * @id ucode/testing/ddns-stat-ast-inventory
 * @tags testing
 */

import codeql.files.FileSystem
import codeql.ucode.ast.internal.TreeSitter

private predicate targetFile(UCODE::AstNode node) {
  node.getLocation().getFile().getRelativePath() = "usr/share/rpcd/ucode/ddns.uc" or
  node.getLocation().getFile().getRelativePath() = "controls/positive-direct.uc" or
  node.getLocation().getFile().getRelativePath() = "controls/positive-post-call-property.uc" or
  node.getLocation().getFile().getRelativePath() = "controls/negative-shadow.uc" or
  node.getLocation().getFile().getRelativePath() = "controls/negative-reassignment.uc" or
  node.getLocation().getFile().getRelativePath() = "controls/negative-other-module.uc" or
  node.getLocation().getFile().getRelativePath() = "controls/negative-fixed-path.uc" or
  node.getLocation().getFile().getRelativePath() = "controls/negative-readfile.uc" or
  node.getLocation().getFile().getRelativePath() = "controls/negative-optional-call.uc" or
  node.getLocation().getFile().getRelativePath() = "controls/negative-aliased-import.uc" or
  node.getLocation().getFile().getRelativePath() = "controls/negative-request-shadow.uc" or
  node.getLocation().getFile().getRelativePath() = "controls/negative-duplicate.uc" or
  node.getLocation().getFile().getRelativePath().matches("model-controls/%") or
  node.getLocation().getFile().getRelativePath() = "usr/share/rpcd/ucode/weechat.uc" or
  node.getLocation().getFile().getRelativePath().matches("rename-controls/%") or
  node.getLocation().getFile().getRelativePath().matches("open-controls/%")
}

private string rawName(UCODE::AstNode node) {
  exists(UCODE::Identifier id | node = id and result = id.getValue())
  or
  exists(UCODE::PropertyIdentifier id | node = id and result = id.getValue())
  or
  not node instanceof UCODE::Identifier and
  not node instanceof UCODE::PropertyIdentifier and
  result = "<not-an-identifier>"
}

from UCODE::AstNode node, UCODE::AstNode parent
where targetFile(node) and parent = node.getParent()
select node.getLocation().getFile().getRelativePath() as source_path,
  node.getAPrimaryQlClass() as node_kind,
  rawName(node) as raw_name,
  node.getLocation().getStartLine() as node_start_line,
  node.getLocation().getStartColumn() as node_start_column,
  node.getLocation().getEndLine() as node_end_line,
  node.getLocation().getEndColumn() as node_end_column,
  node as node_entity,
  parent.getAPrimaryQlClass() as parent_kind,
  parent.getLocation().getStartLine() as parent_start_line,
  parent.getLocation().getStartColumn() as parent_start_column,
  parent.getLocation().getEndLine() as parent_end_line,
  parent.getLocation().getEndColumn() as parent_end_column,
  node.getParentIndex() as child_index,
  parent as parent_entity
