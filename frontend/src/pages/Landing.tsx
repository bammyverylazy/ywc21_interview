import { Nav } from "../components/landing/Nav";
import { FinalCta, Footer, Hero, HowItWorks, Showcase, Transparency, Value } from "../components/landing/Sections";
export default function Landing() {
  return (
    <>
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-app focus:bg-white focus:px-3 focus:py-2">ข้ามไปยังเนื้อหา</a>
      <Nav />
      <main id="main"><Hero /><Value /><HowItWorks /><Showcase /><Transparency /><FinalCta /></main>
      <Footer />
    </>
  );
}
