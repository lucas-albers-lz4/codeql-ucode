import { stat } from 'fs';
const methods = { observe: { args: { service_name: 'service_name' }, call: function(request) {
  if (!request.args.service_name) return null;
  return helper(request.args.service_name);
} } };
return { 'luci.review.helper-function': methods };
function helper(value) { return stat(`${value}`); }
