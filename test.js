async function waitCallback (callback) {
  return new Promise(async (resolve, reject) => {
    callback(resolve, reject)
  })
}