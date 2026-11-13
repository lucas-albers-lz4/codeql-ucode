/**
 * Shared modeling concepts for ucode.
 *
 * `codeql/threat-models` is not a pack dependency. `currentThreatModel` is
 * empty, so `ActiveThreatModelSource` is uninhabited. Not production taint
 * and not `path_found`.
 */

private import codeql.ucode.DataFlow

/**
 * A data flow source, for a specific threat-model.
 *
 * Extend this class to refine existing API models. If you want to model new APIs,
 * extend `ThreatModelSource::Range` instead.
 */
class ThreatModelSource extends DataFlow::Node instanceof ThreatModelSource::Range {
  /**
   * Gets a string that represents the source kind with respect to threat modeling.
   *
   * See
   * - https://github.com/github/codeql/blob/main/docs/codeql/reusables/threat-model-description.rst
   * - https://github.com/github/codeql/blob/main/shared/threat-models/ext/threat-model-grouping.model.yml
   */
  string getThreatModel() { result = super.getThreatModel() }

  /** Gets a string that describes the type of this threat-model source. */
  string getSourceType() { result = super.getSourceType() }
}

/** Provides a class for modeling new sources for specific threat-models. */
module ThreatModelSource {
  /**
   * A data flow source, for a specific threat-model.
   *
   * Extend this class to model new APIs. If you want to refine existing API models,
   * extend `ThreatModelSource` instead.
   */
  abstract class Range extends DataFlow::Node {
    /**
     * Gets a string that represents the source kind with respect to threat modeling.
     *
     * See
     * - https://github.com/github/codeql/blob/main/docs/codeql/reusables/threat-model-description.rst
     * - https://github.com/github/codeql/blob/main/shared/threat-models/ext/threat-model-grouping.model.yml
     */
    abstract string getThreatModel();

    /** Gets a string that describes the type of this threat-model source. */
    abstract string getSourceType();
  }
}

/**
 * Holds if threat-model kind `kind` is enabled.
 *
 * Always empty: `codeql/threat-models` is not a pack dependency. Do not treat
 * this as an enabled default remote-source set.
 */
private predicate currentThreatModel(string kind) { none() }

/**
 * A data flow source that is enabled in the current threat model configuration.
 *
 * Uninhabited until a threat-models pack dependency is added with lockfile
 * discipline.
 */
class ActiveThreatModelSource extends ThreatModelSource {
  ActiveThreatModelSource() {
    exists(string kind |
      currentThreatModel(kind) and
      this.getThreatModel() = kind
    )
  }
}
