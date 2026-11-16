/** Exact call and declaration-name identities for the production Models relation. */
import codeql.ucode.m3.Models

from CallPackageVersionCheckNetifd call, UCODE::FunctionDeclaration declaration
where sameFileCall(call, declaration)
select call, declaration.getName()
