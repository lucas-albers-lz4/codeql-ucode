/**
 * Shared modeling concepts for ucode.
 *
 * `codeql/threat-models` is a pack dependency; `currentThreatModel` comes from
 * that pack. No ucode `ThreatModelSource::Range` models exist yet, so
 * `ActiveThreatModelSource` is uninhabited. Not production taint and not
 * `path_found`.
 */

private import codeql.ucode.DataFlow
private import codeql.threatmodels.ThreatModels

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
 * A data flow source that is enabled in the current threat model configuration.
 *
 * Uninhabited until ucode defines `ThreatModelSource::Range` subclasses. Do not
 * treat this as production taint.
 */
class ActiveThreatModelSource extends ThreatModelSource {
  ActiveThreatModelSource() { currentThreatModel(this.getThreatModel()) }
}
