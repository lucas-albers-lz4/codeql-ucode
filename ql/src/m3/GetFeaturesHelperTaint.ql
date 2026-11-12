/**
 * @name getFeatures netifd helper request.args taint
 * @description Negative control: the selected netifd popen helper must not be request.args-tainted.
 * @kind problem
 * @problem.severity recommendation
 * @id ucode/m3/getfeatures-helper-taint
 * @tags testing
 */

import codeql.ucode.m3.Models

from RequestArgsAccess src, NamedFsPopenCall popen, CallPackageVersionCheckNetifd helperCall,
  UCODE::FunctionDeclaration helper
where
  inGetFeaturesCall(helperCall) and
  sameFileCall(helperCall, helper) and
  popen.getParent*() = helper and
  taintReachesSink(src, popen)
select src, "unexpected request.args taint into the netifd $@ helper", popen, "popen"
