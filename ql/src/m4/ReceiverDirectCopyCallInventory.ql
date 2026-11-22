/** Extracted call-site inventory for the bounded direct-copy controls. */
import codeql.ucode.AST
import codeql.ucode.ast.internal.AstNodes
import codeql.ucode.ast.internal.TreeSitter
from UCODE::CallExpression call
where call.getLocation().getFile().getBaseName() = "direct-copy-controls.uc"
select call, call.getFunction().toString()
