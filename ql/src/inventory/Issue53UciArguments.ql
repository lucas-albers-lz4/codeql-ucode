/**
 * @name Issue 53 UCI controller argument observation
 * @description Test-only inspection of arguments at the pinned controller's forwarding and commit calls.
 * @kind table
 * @id ucode/inventory/issue-53-uci-arguments
 */
import codeql.files.FileSystem
import codeql.ucode.AST

from Call c, int i, Expr arg
where
  arg = c.getArgument(i) and
  arg.getFile().getRelativePath() = "usr/share/ucode/luci/controller/admin/uci.uc" and
  arg.getLocation().getStartLine() in [28, 79]
select arg, i
