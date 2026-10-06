"""Sequential, single-day teaching model. No persistence, auth or networking."""
from dataclasses import dataclass, replace


class Invalid(ValueError):
    pass


class Conflict(ValueError):
    pass


class Forbidden(PermissionError):
    pass


@dataclass(frozen=True)
class Booking:
    id: int
    owner: str
    start: int
    end: int
    status: str = "active"


def validate(actor: str, start: int, end: int) -> None:
    if type(actor) is not str or not actor.strip():
        raise Invalid("actor must be a nonempty string")
    if type(start) is not int or type(end) is not int:
        raise Invalid("minutes must be integers, excluding bool")
    if not 540 <= start < end <= 1020:
        raise Invalid("outside the single-day opening interval")
    if not 30 <= end - start <= 120:
        raise Invalid("duration must be 30 through 120 minutes")


class Schedule:
    def __init__(self) -> None:
        self._bookings: tuple[Booking, ...] = ()
        self._next_id = 1

    def snapshot(self) -> tuple[Booking, ...]:
        return self._bookings

    def reserve(self, actor: str, start: int, end: int) -> Booking:
        validate(actor, start, end)
        if any(b.status == "active" and start < b.end and b.start < end
               for b in self._bookings):
            raise Conflict("requested interval overlaps an active booking")
        booking = Booking(self._next_id, actor, start, end)
        self._bookings += (booking,)
        self._next_id += 1
        return booking

    def cancel(self, actor: str, booking_id: int) -> Booking:
        if type(actor) is not str or not actor.strip():
            raise Invalid("actor must be a nonempty string")
        if type(booking_id) is not int or booking_id <= 0:
            raise Invalid("booking id must be a positive integer, excluding bool")
        for index, booking in enumerate(self._bookings):
            if booking.id != booking_id:
                continue
            if booking.owner != actor:
                raise Forbidden("only the creating actor may cancel")
            if booking.status == "cancelled":
                return booking
            cancelled = replace(booking, status="cancelled")
            self._bookings = (self._bookings[:index] + (cancelled,)
                              + self._bookings[index + 1:])
            return cancelled
        raise KeyError("unknown booking id")


def main() -> None:
    schedule = Schedule()
    first = schedule.reserve("demo", 540, 600)
    print("created", first)
    try:
        schedule.reserve("other", 570, 630)
    except Conflict:
        print("conflict: not created")
    print("adjacent", schedule.reserve("other", 600, 630))
    print("cancelled", schedule.cancel("demo", first.id))
    print("released", schedule.reserve("demo", 540, 600))


if __name__ == "__main__":
    main()
