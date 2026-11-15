/** Scratch observation only: every raw call survives negative classification. */
import codeql.ucode.m3.Models

string flag(UCODE::CallExpression c) {
  if c instanceof NamedFsPopenCall then result = "named-fs-popen" else result = "unresolved"
}

from UCODE::CallExpression c
select c, c.getFunction().toString(), flag(c), c.getLocation().getFile().getRelativePath(),
  c.getLocation().getStartLine(), c.getLocation().getStartColumn(),
  c.getLocation().getEndLine(), c.getLocation().getEndColumn()
