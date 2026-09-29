"use client"

import { useEffect, useMemo, useRef, useState } from "react"
import { createPortal } from "react-dom"
import { CheckIcon, ChevronDownIcon } from "lucide-react"

import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  catalogOptionMatches,
  catalogShortcut,
  rankCatalogMatch,
} from "@/lib/catalog"
import { cn } from "@/lib/utils"

export type ComboboxOption = {
  id: string
  label: string
  group?: string
}

type ComboboxProps = {
  id: string
  name: string
  label: string
  value: string
  options: ComboboxOption[]
  placeholder?: string
  emptyText?: string
  hint?: string
  disabled?: boolean
  required?: boolean
  autoFocus?: boolean
  onChange: (value: string) => void
  onAdvance?: () => void
}

export function Combobox({
  id,
  name,
  label,
  value,
  options,
  placeholder = "Type to search…",
  emptyText = "No matching option.",
  hint,
  disabled,
  required,
  autoFocus,
  onChange,
  onAdvance,
}: ComboboxProps) {
  const [query, setQuery] = useState("")
  const [open, setOpen] = useState(false)
  const [highlight, setHighlight] = useState(0)
  const [menuBox, setMenuBox] = useState<{
    top: number
    left: number
    width: number
  } | null>(null)
  const blurTimer = useRef<number | null>(null)
  const wrapRef = useRef<HTMLDivElement>(null)

  const filtered = useMemo(() => {
    const needle = query.trim()
    const matched = needle
      ? options.filter((option) => catalogOptionMatches(option, needle))
      : options
    if (!needle) {
      return matched
    }
    return [...matched].sort(
      (left, right) =>
        rankCatalogMatch(left, needle) - rankCatalogMatch(right, needle)
    )
  }, [options, query])

  const groups = useMemo(() => {
    const seen = new Map<string, ComboboxOption[]>()
    for (const option of filtered) {
      const key = option.group ?? ""
      const list = seen.get(key) ?? []
      list.push(option)
      seen.set(key, list)
    }
    return Array.from(seen.entries())
  }, [filtered])

  function placeMenu() {
    const el = wrapRef.current
    if (!el) {
      return
    }
    const rect = el.getBoundingClientRect()
    setMenuBox({
      top: rect.bottom + 4,
      left: rect.left,
      width: rect.width,
    })
  }

  useEffect(() => {
    if (!open) {
      return
    }
    placeMenu()
    const onReposition = () => placeMenu()
    window.addEventListener("resize", onReposition)
    window.addEventListener("scroll", onReposition, true)
    return () => {
      window.removeEventListener("resize", onReposition)
      window.removeEventListener("scroll", onReposition, true)
    }
  }, [open])

  function commit(next: string) {
    onChange(next)
    setQuery("")
    setOpen(false)
  }

  function selectIndex(index: number) {
    const option = filtered[index]
    if (option) {
      commit(option.label)
    }
  }

  function onBlur() {
    blurTimer.current = window.setTimeout(() => {
      setOpen(false)
      setQuery("")
    }, 120)
  }

  function onFocus() {
    if (blurTimer.current) {
      window.clearTimeout(blurTimer.current)
    }
    if (!disabled) {
      setOpen(true)
    }
  }

  return (
    <div className="space-y-2">
      <Label htmlFor={id}>{label}</Label>
      <input type="hidden" name={name} value={value} required={required} />
      <div className="relative" ref={wrapRef}>
        <Input
          id={id}
          role="combobox"
          aria-expanded={open}
          aria-controls={`${id}-list`}
          aria-autocomplete="list"
          autoComplete="off"
          autoFocus={autoFocus}
          disabled={disabled}
          placeholder={value || placeholder}
          value={open ? query : value}
          onFocus={onFocus}
          onBlur={onBlur}
          onChange={(event) => {
            setQuery(event.target.value)
            setHighlight(0)
            setOpen(true)
          }}
          onKeyDown={(event) => {
            if (event.key === "ArrowDown") {
              event.preventDefault()
              setOpen(true)
              setHighlight((current) =>
                filtered.length ? (current + 1) % filtered.length : 0
              )
            } else if (event.key === "ArrowUp") {
              event.preventDefault()
              setOpen(true)
              setHighlight((current) =>
                filtered.length
                  ? (current - 1 + filtered.length) % filtered.length
                  : 0
              )
            } else if (event.key === "Enter") {
              event.preventDefault()
              if (open && filtered[highlight]) {
                selectIndex(highlight)
                onAdvance?.()
                return
              }
              if (value) {
                setOpen(false)
                setQuery("")
                onAdvance?.()
              }
            } else if (event.key === "Escape") {
              setOpen(false)
              setQuery("")
            }
          }}
          className="pr-8"
        />
        <ChevronDownIcon className="pointer-events-none absolute top-1/2 right-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
      </div>
      {hint ? (
        <p className="text-xs text-muted-foreground">{hint}</p>
      ) : null}
      {open && !disabled && menuBox && typeof document !== "undefined"
        ? createPortal(
            <div
              id={`${id}-list`}
              role="listbox"
              style={{
                top: menuBox.top,
                left: menuBox.left,
                width: menuBox.width,
              }}
              className="fixed z-50 max-h-64 overflow-auto rounded-xl border border-border bg-popover p-1 text-sm shadow-lg"
            >
              {filtered.length === 0 ? (
                <p className="px-2.5 py-2 text-muted-foreground">{emptyText}</p>
              ) : (
                groups.map(([group, items]) => (
                  <div key={group || "options"}>
                    {group ? (
                      <p className="px-2.5 py-1.5 text-xs font-medium text-muted-foreground">
                        {group}
                      </p>
                    ) : null}
                    {items.map((option) => {
                      const index = filtered.indexOf(option)
                      const selected = option.label === value
                      const shortcut = catalogShortcut(option)
                      return (
                        <button
                          key={option.id}
                          type="button"
                          role="option"
                          aria-selected={selected}
                          className={cn(
                            "flex w-full items-center justify-between gap-3 rounded-lg px-2.5 py-1.5 text-left",
                            index === highlight
                              ? "bg-muted"
                              : "hover:bg-muted/70"
                          )}
                          onMouseDown={(event) => event.preventDefault()}
                          onMouseEnter={() => setHighlight(index)}
                          onClick={() => commit(option.label)}
                        >
                          <span className="min-w-0 truncate">{option.label}</span>
                          <span className="flex shrink-0 items-center gap-2">
                            {shortcut ? (
                              <span className="text-xs text-muted-foreground">
                                {shortcut}
                              </span>
                            ) : null}
                            {selected ? (
                              <CheckIcon className="size-3.5 text-muted-foreground" />
                            ) : null}
                          </span>
                        </button>
                      )
                    })}
                  </div>
                ))
              )}
            </div>,
            document.body
          )
        : null}
    </div>
  )
}
