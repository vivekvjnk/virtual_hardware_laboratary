module.exports = {
  hooks: {
    readPackage(pkg, context) {
      // Allow builds for specific packages that are being ignored
      return pkg;
    }
  }
};
