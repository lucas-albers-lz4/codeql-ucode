/** @name Testing-only UCI commit and fixed restart adjacency
 * @description Exact direct statement adjacency, not execution or causality.
 * @kind table
 * @id ucode/testing/issue53-uci-commit-adjacency
 */
import codeql.ucode.Concepts
import codeql.ucode.m3.Models
import codeql.ucode.ast.internal.TreeSitter

private predicate siblings(UCODE::AstNode owner, int i, UCODE::ExpressionStatement first, UCODE::ExpressionStatement second) {
  exists(UCODE::StatementBlock b | owner = b and first = b.getChild(i) and second = b.getChild(i + 1)) or
  exists(UCODE::SwitchCase c | owner = c and first = c.getBody(i) and second = c.getBody(i + 1))
}
from SourceDeclaredUciCommit commit, BuiltinSystemCall restart,
  UCODE::ExpressionStatement first, UCODE::ExpressionStatement second,
  UCODE::AstNode owner, UCODE::String command, int i
where
  first.getChild() = commit and second.getChild() = restart and siblings(owner, i, first, second) and
  not exists(restart.getOptionalChain()) and command = restart.getArguments().getChild(0) and
  not exists(restart.getArguments().getChild(1)) and
  command.getChild(0).(UCODE::StringFragment).getValue().regexpMatch("/etc/init[.]d/[A-Za-z0-9_-]+ restart >/dev/null 2>&1") and
  not exists(command.getChild(1))
select commit.getLocation().getFile().getRelativePath() as path, commit, restart, owner, i, first, second
