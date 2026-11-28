import { stat } from 'fs';
const methods = { observe: { args: { service_name: 'service_name' }, call: function(request, request) {
  if (!request.args.service_name) return null;
  return stat(`${request.args.service_name}`);
} } };
return { 'luci.review.duplicate-formal': methods };
