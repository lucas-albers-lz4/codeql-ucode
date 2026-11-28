import { stat } from 'fs';
const methods = { observe: { args: { service_name: 'service_name' }, call: function(request) {
  if (!request.args.service_name) return null;
  return function() { return stat(`${request.args.service_name}`); };
} } };
return { 'luci.review.nested-capture': methods };
