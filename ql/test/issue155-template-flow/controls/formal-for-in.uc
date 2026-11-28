import { stat } from 'fs';
const methods = { observe: { args: { service_name: 'service_name' }, call: function(request) {
  if (!request.args.service_name) return null;
  for (request in []) return stat(`${request.args.service_name}`);
        return null;
} } };
return { 'luci.review.formal-for-in': methods };
