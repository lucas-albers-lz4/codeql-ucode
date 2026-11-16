/** Test-only generalized analogue of GetFeaturesHelperTaint, not production. */
import codeql.ucode.m3.Models

from RequestArgsAccess src, NamedFsPopenCall popen, NamedCall helperCall,
  UCODE::FunctionDeclaration helper
where
  helperCall.getName() = "localHelper" and
  inGetFeaturesCall(helperCall) and
  sameFileCall(helperCall, helper) and
  popen.getParent*() = helper and
  taintReachesSink(src, popen)
select src, popen
