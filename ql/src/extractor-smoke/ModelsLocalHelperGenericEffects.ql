/** Test-only generalized analogue of GetFeaturesPopen, not the production query. */
import codeql.ucode.m3.Models

from NamedCall helperCall, UCODE::FunctionDeclaration helper, NamedFsPopenCall popen
where
  helperCall.getName() = "localHelper" and
  inGetFeaturesCall(helperCall) and
  sameFileCall(helperCall, helper) and
  popen.getParent*() = helper
select helperCall, popen
