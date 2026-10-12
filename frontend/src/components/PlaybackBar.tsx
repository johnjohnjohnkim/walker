import type { DecodedTrace } from '../trace'
import { visitsUpTo } from '../trace'
import { SPEEDS, type Playback } from '../usePlayback'

interface Props {
  trace: DecodedTrace
  playback: Playback
  algorithmName: string
}

/** Play, pause, scrub and change speed for the search animation. */
export function PlaybackBar({ trace, playback, algorithmName }: Props) {
  const { step, playing, speed, finished } = playback
  const explored = visitsUpTo(trace, step)

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
        aria-valuetext={`${explored} of ${trace.visited} intersections explored`}
      />
      <span className="playback__label">
        {algorithmName}: {explored.toLocaleString('en-US')} / {trace.visited.toLocaleString('en-US')} explored
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
