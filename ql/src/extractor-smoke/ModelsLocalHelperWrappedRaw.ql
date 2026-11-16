/** Raw outer unsupported call shapes; do not depend on NamedCall. */
import codeql.ucode.m3.Models

from UCODE::CallExpression call
where
  call.getLocation().getFile().getRelativePath() =
    ["member.uc", "parenthesized.uc", "sequence.uc", "subscript.uc", "nested_call.uc"] and
  stringLiteralValue(call.getArguments().getChild(0).(UCODE::String)) = "netifd"
select call
