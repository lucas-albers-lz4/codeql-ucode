/** @name Testing-only open literal mode guard counterfactual
 * @description Selects any literal mode rather than r; tests the mode-value guard.
 * @kind table
 * @id ucode/testing/issue155-open-read-any-literal-mode
 * @tags testing
 */
import codeql.files.FileSystem
import codeql.ucode.ast.internal.TreeSitter
import codeql.ucode.internal.SourceDeclaredFs
from UCODE::CallExpression call, UCODE::AstNode pathArg, UCODE::String mode
where sourceDeclaredFsCall(call, "open") and pathArg = call.getArguments().getChild(0) and
  pathArg instanceof UCODE::Expression and mode = call.getArguments().getChild(1) and
  mode.getChild(0) instanceof UCODE::StringFragment and not exists(mode.getChild(1)) and
  (not exists(call.getArguments().getChild(2)) or call.getArguments().getChild(2) instanceof UCODE::Expression) and
  not exists(int i | i != 0 and i != 1 and i != 2 and exists(call.getArguments().getChild(i)))
select call.getLocation().getFile().getRelativePath() as path, call as call_node,
  call.getFunction() as callee_node, pathArg as path_node, mode as mode_node
