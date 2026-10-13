import { useEffect, useId, useRef, useState } from 'react'
import { ApiError, fetchPlaces, type Place } from '../api'

interface Props {
  label: string
  placeholder: string
  // What the box shows when the user isn't typing: the chosen place's name.
  value: string
  marker: 'origin' | 'destination'
  onSelect: (place: Place) => void
}

const DEBOUNCE_MS = 250
const MIN_QUERY = 2

// Each answer remembers the query it was for, so results for "union" are
// never shown (or picked with Enter) once the box says "union station".
type Suggestions =
  | { kind: 'none' }
  | { kind: 'results'; query: string; places: Place[] }
  | { kind: 'error'; query: string; message: string }

/** A place search field with autocomplete, keyboard navigation and screen-reader roles. */
export function SearchBox({ label, placeholder, value, marker, onSelect }: Props) {
  const [text, setText] = useState(value)
  const [editing, setEditing] = useState(false)
  // True once the user has changed the text since focusing. Focusing fills the
  // box with the chosen place's label ("Dropped pin", "CN Tower"), which is
  // not something to search for.
  const [typed, setTyped] = useState(false)
  const [suggestions, setSuggestions] = useState<Suggestions>({ kind: 'none' })
  const [active, setActive] = useState(-1)
  const listId = useId()
  const inputRef = useRef<HTMLInputElement>(null)

  // Show the chosen place when the user isn't typing.
  const shown = editing ? text : value
  const query = text.trim()
  const shouldSearch = editing && typed && query.length >= MIN_QUERY

  useEffect(() => {
    if (!shouldSearch) return
    const controller = new AbortController()
    const timer = setTimeout(() => {
      fetchPlaces(query, controller.signal)
        .then((places) => {
          setSuggestions({ kind: 'results', query, places })
          setActive(places.length > 0 ? 0 : -1)
        })
        .catch((error: unknown) => {
          if (controller.signal.aborted) return
          const message = error instanceof ApiError ? error.message : 'Place search is unavailable right now.'
          setSuggestions({ kind: 'error', query, message })
        })
    }, DEBOUNCE_MS)
    return () => {
      clearTimeout(timer)
      controller.abort()
    }
  }, [query, shouldSearch])

  const current = shouldSearch && suggestions.kind !== 'none' && suggestions.query === query ? suggestions : null
  const places = current?.kind === 'results' ? current.places : []
  const open = places.length > 0
  let status = ''
  if (shouldSearch && !current) status = 'Searching…'
  else if (current?.kind === 'error') status = current.message
  else if (current?.kind === 'results') {
    status = places.length === 0 ? 'No places found on the map.' : `${places.length} suggestions`
  }

  function choose(place: Place) {
    onSelect(place)
    setEditing(false)
    setSuggestions({ kind: 'none' })
    inputRef.current?.blur()
  }

  function onKeyDown(event: React.KeyboardEvent<HTMLInputElement>) {
    if (event.key === 'ArrowDown' && places.length > 0) {
      event.preventDefault()
      setActive((i) => (i + 1) % places.length)
    } else if (event.key === 'ArrowUp' && places.length > 0) {
      event.preventDefault()
      setActive((i) => (i <= 0 ? places.length - 1 : i - 1))
    } else if (event.key === 'Enter' && active >= 0 && active < places.length) {
      event.preventDefault()
      choose(places[active])
    } else if (event.key === 'Escape') {
      setEditing(false)
      setSuggestions({ kind: 'none' })
    }
  }

  return (
    <div className="search">
      <span className={`search__marker search__marker--${marker}`} aria-hidden="true" />
      <input
        ref={inputRef}
        className="search__input"
        type="text"
        role="combobox"
        aria-label={label}
        aria-expanded={open}
        aria-controls={open ? listId : undefined}
        aria-autocomplete="list"
        aria-activedescendant={open && active >= 0 ? `${listId}-${active}` : undefined}
        placeholder={placeholder}
        value={shown}
        onFocus={(event) => {
          setText(value)
          setEditing(true)
          setTyped(false)
          event.currentTarget.select()
        }}
        onChange={(event) => {
          setText(event.target.value)
          setEditing(true)
          setTyped(true)
        }}
        // Suggestions are picked on mousedown with preventDefault, so the
        // input keeps focus while one is clicked and blur can act at once.
        onBlur={() => setEditing(false)}
        onKeyDown={onKeyDown}
      />
      {/* Announced by screen readers; shown when there is nothing to pick. */}
      <div
        className={`search__note${current?.kind === 'error' ? ' search__note--error' : ''}${
          status && !open ? ' search__note--visible' : ''
        }`}
        role="status"
        aria-live="polite"
      >
        {status}
      </div>
      {open && (
        <ul className="search__list" id={listId} role="listbox" aria-label={`${label} suggestions`}>
          {places.map((place, i) => (
            <li
              key={`${place.name}|${place.address}|${place.lon}|${place.lat}`}
              id={`${listId}-${i}`}
              role="option"
              aria-selected={i === active}
              className={`search__option${i === active ? ' search__option--active' : ''}`}
              // mousedown, not click, so it fires before the input's blur.
              onMouseDown={(event) => {
                event.preventDefault()
                choose(place)
              }}
              onMouseEnter={() => setActive(i)}
            >
              <span className="search__name">{place.name}</span>
              {place.address && <span className="search__address">{place.address}</span>}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
