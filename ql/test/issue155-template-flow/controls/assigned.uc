import { stat } from 'fs';
const methods = { observe: { args: { service_name: 'service_name' }, call: function(request) {
  if (!request.args.service_name) return null;
  const service = request.args.service_name;
  return stat(`${service}`);
} } };
return { 'luci.review.assigned': methods };
