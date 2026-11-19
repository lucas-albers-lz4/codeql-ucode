const methods = {
  setBlockDetect: { call: function(request) {
    if (!request.allowed) return { result: false };
    return { result: system('/bin/true') == 0 };
  } }
};
return { luci: methods };
