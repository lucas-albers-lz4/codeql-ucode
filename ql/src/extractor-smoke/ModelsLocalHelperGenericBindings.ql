/** General Models relation on a second helper name and argument. */
import codeql.ucode.m3.Models

from NamedCall call, UCODE::FunctionDeclaration declaration
where call.getName() = "localHelper" and sameFileCall(call, declaration)
select call, declaration.getName()
