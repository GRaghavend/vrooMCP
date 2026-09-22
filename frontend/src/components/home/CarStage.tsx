import type { CSSProperties } from "react";
import showroom from "../../assets/showroom.png";

/**
 * The showroom artwork is one flat image, so each car is revealed by masking the same
 * image to a horizontal band. Bands are [from%, to%] of the width, cut between neighbours.
 */
const CARS = [
  { name: "Audi", from: 0, to: 22.5 },
  { name: "INFINITI", from: 22.5, to: 41 },
  { name: "Mercedes-Benz", from: 41, to: 60.5 },
  { name: "Lexus", from: 60.5, to: 78 },
  { name: "BMW", from: 78, to: 100 },
];
// Centre car first, then outward — reads as a curtain opening rather than a left-to-right wipe.
const ENTRY_ORDER = [2, 1, 3, 0, 4];

export default function CarStage() {
  return (
    <div className="stage" aria-hidden="true">
      <div className="stage__glow stage__glow--a" />
      <div className="stage__glow stage__glow--b" />
      <div className="stage__art" style={{ "--art": `url(${showroom})` } as CSSProperties}>
        <div className="stage__layer stage__layer--base" />
        {CARS.map((car, i) => (
          <div
            key={car.name}
            className="stage__layer stage__layer--car"
            style={
              {
                "--from": `${car.from}%`,
                "--to": `${car.to}%`,
                "--edge-l": car.from === 0 ? "0%" : "2.5%",
                "--edge-r": car.to === 100 ? "0%" : "2.5%",
                "--delay": `${0.5 + ENTRY_ORDER.indexOf(i) * 0.16}s`,
              } as CSSProperties
            }
          />
        ))}
      </div>
      <div className="stage__vignette" />
    </div>
  );
}
