import type { DecodedTrace } from '../trace'
import { visitsUpTo } from '../trace'
import { SPEEDS, type Playback } from '../usePlayback'

interface Props {
  trace: DecodedTrace
  playback: Playback
  algorithmName: string
  // The search's real number of visits (the trace may be a sample).
  totalVisited: number
}

/** Play, pause, scrub and change speed for the search animation. */
export function PlaybackBar({ trace, playback, algorithmName, totalVisited }: Props) {
  const { step, playing, speed, finished } = playback
  // Scale the sample's progress up to the real search.
  const shown = visitsUpTo(trace, step)
  // A truncated trace stops before the search did, so it can only be scaled
  // by its sampling stride, not stretched to the search's full total.
  const explored = trace.truncated
    ? Math.min(totalVisited, shown * trace.stride)
    : finished
      ? totalVisited
      : trace.visited > 0
        ? Math.round((shown / trace.visited) * totalVisited)
        : 0

  return (
    <section className="playback" aria-label="Search animation">
      <button
        type="button"
        className="playback__play"
        onClick={playback.toggle}
        aria-label={playing ? 'Pause' : finished ? 'Replay' : 'Play'}
      >
        {playing ? '❚❚' : finished ? '↺' : '▶'}
      </button>
      <input
        className="playback__scrubber"
        type="range"
        min={0}
        max={trace.steps}
        value={step}
        onChange={(event) => playback.seek(Number(event.target.value))}
        aria-label="Animation position"
        aria-valuetext={`${explored} of ${totalVisited} intersections explored`}
      />
      <span className="playback__label">
        {algorithmName}: {explored.toLocaleString('en-US')} / {totalVisited.toLocaleString('en-US')} explored
        {trace.stride > 1 && ` (showing every ${ordinal(trace.stride)} step)`}
        {trace.truncated && ' (trace cut short)'}
      </span>
      <div className="playback__speeds" role="group" aria-label="Speed">
        {SPEEDS.map((s) => (
          <button
            key={s}
            type="button"
            className={`playback__speed${s === speed ? ' playback__speed--selected' : ''}`}
            aria-pressed={s === speed}
            onClick={() => playback.setSpeed(s)}
          >
            {s}×
          </button>
        ))}
      </div>
      {!finished && (
        <button type="button" className="playback__skip" onClick={playback.skipToEnd}>
          Skip
        </button>
      )}
    </section>
  )
}

function ordinal(n: number): string {
  const suffix = n % 100 >= 11 && n % 100 <= 13 ? 'th' : ({ 1: 'st', 2: 'nd', 3: 'rd' } as Record<number, string>)[n % 10] ?? 'th'
  return `${n}${suffix}`
}
