import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import Blotter from "./pages/Blotter";
import FxDesk from "./pages/FxDesk";
import Market3D from "./pages/Market3D";
import MarketIntelligence from "./pages/MarketIntelligence";
import Overview from "./pages/Overview";
import RatesBonds from "./pages/RatesBonds";
import Risk from "./pages/Risk";
import Scenario from "./pages/Scenario";
import YieldCurve from "./pages/YieldCurve";

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/fx" element={<FxDesk />} />
          <Route path="/rates" element={<RatesBonds />} />
          <Route path="/yield-curve" element={<YieldCurve />} />
          <Route path="/risk" element={<Risk />} />
          <Route path="/scenario" element={<Scenario />} />
          <Route path="/blotter" element={<Blotter />} />
          <Route path="/vision" element={<MarketIntelligence />} />
          <Route path="/3d" element={<Market3D />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}
