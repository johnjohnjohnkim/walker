import type { AlgorithmInfo } from '../api'

interface Props {
  algorithms: AlgorithmInfo[]
  selected: string
  onSelect: (id: string) => void
}

/** A row of chips in the style of Google Maps' travel modes, one per algorithm. */
export function AlgorithmPicker({ algorithms, selected, onSelect }: Props) {
  const current = algorithms.find((a) => a.id === selected)

  return (
    <div className="picker">
      <div className="picker__chips" role="radiogroup" aria-label="Search algorithm">
        {algorithms.map((algorithm) => {
          const isSelected = algorithm.id === selected
          return (
            <button
              key={algorithm.id}
              type="button"
              role="radio"
              aria-checked={isSelected}
              className={`picker__chip${isSelected ? ' picker__chip--selected' : ''}`}
              disabled={!algorithm.implemented}
              title={algorithm.implemented ? algorithm.description : `${algorithm.name}: not implemented yet`}
              onClick={() => onSelect(algorithm.id)}
            >
              {algorithm.name}
            </button>
          )
        })}
      </div>
      {current && <p className="picker__description">{current.description}</p>}
    </div>
  )
}
