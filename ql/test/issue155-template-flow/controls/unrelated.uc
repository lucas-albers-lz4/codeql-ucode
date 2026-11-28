import { stat } from 'fs';
const methods = { observe: { args: { service_name: 'service_name' }, call: function(request) {
  if (!request.args.service_name) return null;
  const other = { request: { args: { service_name: 'fixed' } } };
  return stat(`${other.request.args.service_name}`);
} } };
return { 'luci.review.unrelated': methods };
