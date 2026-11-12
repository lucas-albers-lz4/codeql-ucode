/**
 * @name getFeatures callPackageVersionCheck popen
 * @description M3: getFeatures.call → callPackageVersionCheck('netifd') and named fs popen in that helper.
 * @kind problem
 * @problem.severity recommendation
 * @id ucode/m3/getfeatures-popen
 * @tags testing
 */

import codeql.ucode.m3.Models

from
  CallPackageVersionCheckNetifd helperCall, UCODE::FunctionDeclaration helper,
  NamedFsPopenCall popen
where
  inGetFeaturesCall(helperCall) and
  sameFileCall(helperCall, helper) and
  popen.getParent*() = helper
select helperCall,
  "getFeatures.call invokes callPackageVersionCheck('netifd') whose body calls named fs $@.", popen,
  "popen"
