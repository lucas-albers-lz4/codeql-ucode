import { stat } from 'fs';
const methods = { observe: { args: { service_name: 'service_name' }, call: function(request) {
  if (!request.args.service_name) return null;
  return stat(`${'/fixed/path'}`);
} } };
return { 'luci.review.fixed': methods };
