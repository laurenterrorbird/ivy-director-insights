# SeminarDesk Webhook Fields Reference

This document lists all fields available in the SeminarDesk webhook payloads based on the examples provided.

## Top-Level Booking Fields

| Field | Type | Description |
|-------|------|-------------|
| `action` | String | Action type: `booking.create`, `booking.update`, `booking.changestatus` |
| `payload.id` | Number | Unique booking ID |
| `payload.notes` | String | Booking notes |
| `payload.tasks` | String | Associated tasks |
| `payload.objectInfo.createdAt` | ISO DateTime | When booking was created |
| `payload.objectInfo.createdBy` | Object/null | User who created (username, firstName, lastName, email, phone, department, roleName, etc.) |
| `payload.objectInfo.changedAt` | ISO DateTime | Last modification timestamp |
| `payload.objectInfo.changedBy` | Object/null | User who last modified (same structure as createdBy) |
| `payload.booker.id` | Number | ID of person who made the booking |
| `payload.booker.name` | String | Name of person who made the booking |
| `payload.status` | String | Booking status: `PENDING`, `CONFIRMED`, `WAIT_LIST`, `CANCELLED` |
| `payload.externalRemarks` | String | Remarks visible to customer |
| `payload.internalRemarks` | String | Internal staff-only remarks |
| `payload.paymentMethod` | Object/null | Payment method information |
| `payload.specialRequestsPriceList` | Object/null | Special pricing list (id, name) |
| `payload.labels` | String | Booking labels |
| `payload.marker` | String | Booking marker/tag |
| `payload.referenceNumbers` | String | Reference numbers |
| `payload.voucherCode` | String | Discount voucher code used |
| `payload.numberOfInvoices` | Number | Count of invoices generated |
| `payload.openBalance` | Number | Remaining balance to be paid |
| `payload.payments` | Array/Object | Payment records (see Payments section below) |
| `payload.externalIdentifier` | String | External system identifier |
| `payload.externalReferences` | String | External references |
| `payload.onlinePaymentStatus` | String | Online payment status: `PENDING`, `null`, etc. |
| `payload.confirmationDate` | ISO DateTime/null | When booking was confirmed |
| `payload.confirmedBy` | String/null | Email/username of person who confirmed |

## Guest-Level Fields (within `payload.guests` array)

Each booking can have one or more guests. Each guest object contains:

| Field | Type | Description |
|-------|------|-------------|
| `id` | Number | Unique guest ID for this booking |
| `guest.profile.id` | Number | Profile ID of the guest |
| `guest.profile.name` | String | Guest's name |
| `guest.name` | String | Guest name (may differ from profile) |
| `guest.age` | Number | Guest age |
| `guest.gender` | String | `MALE`, `FEMALE`, etc. |
| `eventDate.id` | Number | Event date instance ID |
| `eventDate.name` | String | Event date label (includes date range) |
| `event.id` | Number | Event type ID |
| `event.name` | String | Event name (e.g., "Bénévole", "Retraite de Shiné") |
| `status` | String | Guest status: `PENDING`, `CONFIRMED`, `WAIT_LIST` |
| `guestType.id` | Number | Guest type ID |
| `guestType.name` | String | Guest type name (e.g., "Participant") |
| `guestType.type` | String | Guest type code: `PARTICIPANT`, etc. |
| `priceLevel.id` | Number | Price level ID |
| `priceLevel.name` | String | Price level name (e.g., "Résident", "Membre Bienfaiteur") |
| `remarks` | String | Guest-specific remarks |
| `specialRequests` | String | Special requests for this guest |
| `teachingUnits` | Number | Teaching units count |
| `marker` | String | Guest marker/tag |
| `attendanceType` | String | `ON_SITE`, `ONLINE`, etc. |
| `begin` | ISO DateTime | Guest's arrival/start time |
| `end` | ISO DateTime | Guest's departure/end time |
| `voucherCode` | String | Guest-specific voucher code |

## Item Fields (within `items` array for each guest)

Each guest has an array of items (event fees, meals, accommodation, misc):

| Field | Type | Description |
|-------|------|-------------|
| `id` | Number | Unique item ID |
| `type.type` | String | Item type: `EVENT`, `MEALS`, `ACCOMMODATION`, `MISC` |
| `type.logicalType` | String | Logical type (same as type.type or `null` for MISC) |
| `status` | String | Item status: `PENDING`, `CONFIRMED`, `WAIT_LIST` |
| `begin` | ISO DateTime | Item start date/time |
| `end` | ISO DateTime | Item end date/time |
| `text` | String | Item description (e.g., "Repas", "Hébergement Dortoir") |
| `priceList.id` | Number | Price list ID |
| `priceList.name` | String | Price list name (e.g., "Standard", "FSS") |
| `priceListItemId` | Number/null | Specific price list item ID |
| `calculatedPrice` | Number | Calculated price before adjustments |
| `actualPrice` | Number | Final price charged |
| `taxRate.value` | Number | Tax rate (e.g., 0, 0.1 for 10%) |
| `quantity` | Number/null | Quantity (usually null for these items) |

## Payment Fields (within `payload.payments`)

Payments can be an array or single object:

| Field | Type | Description |
|-------|------|-------------|
| `id` | Number | Payment ID |
| `method.code` | String | Payment method code (e.g., "STRIPE CBM") |
| `amount` | Number | Payment amount |
| `date` | Date | Payment date (YYYY-MM-DD format) |
| `remarks` | String | Payment remarks/notes |

## Additional Field Values (Custom Fields)

Custom fields are stored in `additionalFieldValues` arrays (appears at both booking and guest levels):

| Field | Type | Description |
|-------|------|-------------|
| `field.id` | Number | Custom field ID |
| `field.name` | String | Field name (e.g., "Heure d'arrivée", "Langue de réservation") |
| `value` | String | Field value entered by user |
| `source` | String | Source of value: "Booking", "Réservation", "Not filled in", "Non renseigné", email address |
| `objectInfo.createdAt` | ISO DateTime | When field was set |
| `objectInfo.createdBy` | Object/null | Who set the field |
| `objectInfo.changedAt` | ISO DateTime | Last change timestamp |
| `objectInfo.changedBy` | Object/null | Who last changed it |

### Common Custom Fields Observed:

- **Field ID 30**: "Heure d'arrivée" - Arrival time notes
- **Field ID 31**: "Heure de départ" - Departure time notes  
- **Field ID 33**: "Langue de réservation" - Booking language
- **Field ID 2**: "Assise" - Seating preference (Chaise/Coussin)
- **Field ID 5**: "Handicap & Allergie grave" - Handicap & serious allergies
- **Field ID 7**: "Quest. de santé shiné" - Health questionnaire for shiné retreats
- **Field ID 8**: "A reçu enseignements ?" - Has received teachings
- **Field ID 9**: "Carte membre" - Member card status
- **Field ID 10**: "Logt : 2nd choix" - Second choice lodging preference
- **Field ID 11**: "Même logt que" - Same lodging as (another guest)
- **Field ID 13**: "Assise (ENG-FR)" - Seating preference (bilingual)
- **Field ID 14**: "Carte membre (ENG-FR)" - Member card (bilingual)
- **Field ID 15**: "Handicap (ENG-FR)" - Handicap (bilingual)
- **Field ID 16**: "Logt : 2nd choix (ENG-FR)" - Second choice lodging (bilingual)
- **Field ID 26**: "Quest. de santé vipassana (ENG-FR)" - Health questionnaire vipassana (bilingual)
- **Field ID 34**: "Service FPMT?" - FPMT service information

## Data Structure Summary

```
{
  action: "booking.create|update|changestatus",
  payload: {
    id: number,
    booker: { id, name },
    status: string,
    guests: [
      {
        id: number,
        guest: { profile: { id, name }, name, age, gender },
        event: { id, name },
        eventDate: { id, name },
        items: [
          {
            id, type, status, begin, end, text,
            priceList: { id, name },
            calculatedPrice, actualPrice, taxRate: { value }
          }
        ],
        additionalFieldValues: [
          {
            field: { id, name },
            value, source,
            objectInfo: { createdAt, createdBy, changedAt, changedBy }
          }
        ]
      }
    ],
    payments: { id, method: { code }, amount, date, remarks },
    openBalance: number,
    ...
  }
}
```

## Notes

- Dates are in ISO 8601 format with UTC timezone (e.g., `2025-12-10T23:01:00.000Z`)
- Prices are decimal numbers (e.g., `279.25`)
- Some fields may be `null` or empty strings
- The `additionalFieldValues` array appears at both the booking level and guest level
- Multiple guests can share the same booking (e.g., couples booking together)
- Each guest can have multiple items (event fee, meals, accommodation, misc charges)

